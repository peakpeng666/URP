import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = ['CADAModel']


class CADAModel(nn.Module):

    def __init__(self, **model_params):
        super().__init__()
        self.model_params = model_params
        self.eval_type = self.model_params['eval_type']
        self.problem = self.model_params['problem']
        self.use_control_branch = self.model_params.get('use_control_branch', False)
        self.control_guidance_dim = self.model_params.get('control_guidance_dim', 5)

        self.encoder = MTL_Encoder(**model_params)
        self.decoder = MTL_Decoder(**model_params)
        self.encoded_nodes = None  # shape: (batch, problem+1, EMBEDDING_DIM)
        default_device = (
            torch.device('cuda', torch.cuda.current_device())
            if torch.cuda.is_available() else torch.device('cpu')
        )
        self.device = model_params.get('device', default_device)
        if self.use_control_branch:
            init_guidance = self.model_params.get('control_guidance', [1.0] * self.control_guidance_dim)
            if len(init_guidance) != self.control_guidance_dim:
                raise ValueError("control_guidance length must match control_guidance_dim")
            init_alpha = self.model_params.get('control_init_alpha', 0.02)
            self.register_buffer(
                'control_guidance',
                torch.tensor(init_guidance, dtype=torch.float).reshape(1, -1),
            )
            self.control_alpha = nn.Parameter(torch.tensor(float(init_alpha), dtype=torch.float))
        # assert self.model_params['norm'] == "batch", "The original MTLModel implementation uses batch normalization."

    def pre_forward(self, reset_state):
        depot_xy = reset_state.depot_xy
        # shape: (batch, 1, 2)
        node_xy = reset_state.node_xy
        # shape: (batch, problem, 2)
        node_demand = reset_state.node_demand
        node_service_time = reset_state.node_service_time
        node_tw_start = reset_state.node_tw_start
        node_tw_end = reset_state.node_tw_end
        # shape: (batch, problem)
        linehaul_demand = node_demand.clamp_min(0)
        backhaul_demand = (-node_demand).clamp_min(0)
        node_features = torch.cat(
            (
                linehaul_demand[:, :, None],
                backhaul_demand[:, :, None],
                node_tw_start[:, :, None],
                node_tw_end[:, :, None],
                node_service_time[:, :, None],
                node_xy,
            ),
            dim=2,
        )
        # shape: (batch, problem, 7)

        constraint_tag = reset_state.prob_emb
        if constraint_tag.dim() == 1:
            constraint_tag = constraint_tag.unsqueeze(0)
        if constraint_tag.size(0) == 1:
            constraint_tag = constraint_tag.expand(depot_xy.size(0), -1)
        elif constraint_tag.size(0) != depot_xy.size(0):
            raise ValueError(
                "The constraint tag batch dimension must be 1 or match depot_xy. "
                f"Got {constraint_tag.size(0)} and {depot_xy.size(0)}."
            )
        constraint_tag = constraint_tag.to(device=depot_xy.device, dtype=depot_xy.dtype)

        if self.use_control_branch:
            self.encoded_nodes = self.encoder(
                depot_xy,
                node_features,
                constraint_tag,
                guidance=self.control_guidance,
                alpha=self.control_alpha,
            )
        else:
            self.encoded_nodes = self.encoder(depot_xy, node_features, constraint_tag)
        # shape: (batch, problem+1, embedding)
        self.decoder.set_kv(self.encoded_nodes)

    def set_eval_type(self, eval_type):
        self.eval_type = eval_type

    def set_control_guidance(self, guidance=None, alpha=None):
        """Update the runtime LLM/statistical guidance without rebuilding the model."""
        if not self.use_control_branch:
            return
        if guidance is not None:
            guidance = torch.as_tensor(
                guidance,
                dtype=self.control_guidance.dtype,
                device=self.control_guidance.device,
            ).reshape(1, -1)
            if guidance.size(-1) != self.control_guidance_dim:
                raise ValueError("control guidance dimension mismatch")
            self.control_guidance.copy_(guidance)
        if alpha is not None:
            with torch.no_grad():
                self.control_alpha.fill_(float(alpha))

    def forward(self, state, selected=None):
        batch_size = state.BATCH_IDX.size(0)
        pomo_size = state.BATCH_IDX.size(1)

        if state.selected_count == 0:  # First Move, depot
            selected = torch.zeros(size=(batch_size, pomo_size), dtype=torch.long).to(self.device)
            prob = torch.ones(size=(batch_size, pomo_size))
            # probs = torch.ones(size=(batch_size, pomo_size, self.encoded_nodes.size(1)))
            # shape: (batch, pomo, problem_size+1)

            # # Use Averaged encoded nodes for decoder input_1
            # encoded_nodes_mean = self.encoded_nodes.mean(dim=1, keepdim=True)
            # # shape: (batch, 1, embedding)
            # self.decoder.set_q1(encoded_nodes_mean)

            # # Use encoded_depot for decoder input_2
            # encoded_first_node = self.encoded_nodes[:, [0], :]
            # # shape: (batch, 1, embedding)
            # self.decoder.set_q2(encoded_first_node)

        elif state.selected_count == 1:  # Second Move, POMO
            # selected = torch.arange(start=1, end=pomo_size+1)[None, :].expand(batch_size, -1).to(self.device)
            selected = state.START_NODE
            prob = torch.ones(size=(batch_size, pomo_size))
            # probs = torch.ones(size=(batch_size, pomo_size, self.encoded_nodes.size(1)))

        else:
            encoded_last_node = _get_encoding(self.encoded_nodes, state.current_node)
            # shape: (batch, pomo, embedding)
            attr = torch.cat((state.load[:, :, None], state.current_time[:, :, None], state.length[:, :, None], state.open[:, :, None]), dim=2)
            # shape: (batch, pomo, 4)
            probs = self.decoder(encoded_last_node, attr, ninf_mask=state.ninf_mask)
            # shape: (batch, pomo, problem+1)
            if selected is None:
                while True:
                    if self.training or self.eval_type == 'softmax':
                        try:
                            selected = probs.reshape(batch_size * pomo_size, -1).multinomial(1).squeeze(dim=1).reshape(batch_size, pomo_size)
                        except Exception as exception:
                            print(">> Catch Exception: {}, on the instances of {}".format(exception, state.PROBLEM))
                            exit(0)
                    else:
                        selected = probs.argmax(dim=2)
                    prob = probs[state.BATCH_IDX, state.POMO_IDX, selected].reshape(batch_size, pomo_size)
                    # shape: (batch, pomo)
                    if (prob != 0).all():
                        break
            else:
                selected = selected
                prob = probs[state.BATCH_IDX, state.POMO_IDX, selected].reshape(batch_size, pomo_size)

        return selected, prob


def _get_encoding(encoded_nodes, node_index_to_pick):
    # encoded_nodes.shape: (batch, problem, embedding)
    # node_index_to_pick.shape: (batch, pomo)

    batch_size = node_index_to_pick.size(0)
    pomo_size = node_index_to_pick.size(1)
    embedding_dim = encoded_nodes.size(2)

    gathering_index = node_index_to_pick[:, :, None].expand(batch_size, pomo_size, embedding_dim)
    # shape: (batch, pomo, embedding)

    picked_nodes = encoded_nodes.gather(dim=1, index=gathering_index)
    # shape: (batch, pomo, embedding)

    return picked_nodes


########################################
# ENCODER
########################################

class MTL_Encoder(nn.Module):
    def __init__(self, **model_params):
        super().__init__()
        self.model_params = model_params
        embedding_dim = self.model_params['embedding_dim']
        encoder_layer_num = self.model_params['encoder_layer_num']
        self.use_control_branch = self.model_params.get('use_control_branch', False)
        self.control_guidance_dim = self.model_params.get('control_guidance_dim', 5)

        self.embedding_depot = nn.Linear(2, embedding_dim)
        self.embedding_node = nn.Linear(7, embedding_dim)
        self.constraint_prompt = ConstraintPrompt(embedding_dim)

        # CaDA uses a Top-k sparse branch and a globally connected branch.
        self.sparse_layers = nn.ModuleList([
            CaDAEncoderLayer(use_sparse_attention=True, **model_params)
            for _ in range(encoder_layer_num)
        ])
        self.global_layers = nn.ModuleList([
            CaDAEncoderLayer(use_sparse_attention=False, **model_params)
            for _ in range(encoder_layer_num)
        ])
        self.global_to_sparse = nn.ModuleList([
            nn.Linear(embedding_dim, embedding_dim)
            for _ in range(encoder_layer_num)
        ])
        self.sparse_to_global = nn.ModuleList([
            nn.Linear(embedding_dim, embedding_dim)
            for _ in range(max(encoder_layer_num - 1, 0))
        ])
        if self.use_control_branch:
            control_hidden_dim = self.model_params.get('control_hidden_dim', embedding_dim)
            self.control_layers = nn.ModuleList([
                SideControlBranch(
                    embedding_dim=embedding_dim,
                    control_cond_dim=2 * self.control_guidance_dim,
                    control_hidden_dim=control_hidden_dim,
                )
                for _ in range(encoder_layer_num)
            ])

    def forward(self, depot_xy, node_features, constraint_tag, guidance=None, alpha=None):
        # depot_xy.shape: (batch, 1, 2)
        # node_features.shape: (batch, problem, 7)
        # constraint_tag.shape: (batch, 5), ordered as [C, O, B, L, TW]

        embedded_depot = self.embedding_depot(depot_xy)
        # shape: (batch, 1, embedding)
        embedded_node = self.embedding_node(node_features)
        # shape: (batch, problem, embedding)

        initial_nodes = torch.cat((embedded_depot, embedded_node), dim=1)
        # shape: (batch, problem+1, embedding)
        node_count = initial_nodes.size(1)

        sparse_nodes = initial_nodes
        prompt = self.constraint_prompt(constraint_tag)
        global_stream = torch.cat((initial_nodes, prompt), dim=1)
        control_cond = (
            self._build_control_condition(initial_nodes, constraint_tag, guidance)
            if self.use_control_branch else None
        )

        for layer_idx, (sparse_layer, global_layer) in enumerate(
                zip(self.sparse_layers, self.global_layers)):
            sparse_nodes = sparse_layer(sparse_nodes)
            global_stream = global_layer(global_stream)

            global_nodes = global_stream[:, :node_count]
            sparse_nodes = sparse_nodes + self.global_to_sparse[layer_idx](global_nodes)
            if self.use_control_branch:
                sparse_nodes = self.control_layers[layer_idx](sparse_nodes, control_cond, alpha)

            # No next global layer consumes the final fusion, so the official
            # CaDA implementation omits this projection after the last layer.
            if layer_idx < len(self.sparse_to_global):
                global_nodes = global_nodes + self.sparse_to_global[layer_idx](sparse_nodes)
                prompt = global_stream[:, node_count:]
                global_stream = torch.cat((global_nodes, prompt), dim=1)

        return sparse_nodes
        # shape: (batch, problem+1, embedding)

    def _build_control_condition(self, nodes, constraint_tag, guidance):
        batch_size = nodes.size(0)
        constraint_tag = constraint_tag.to(device=nodes.device, dtype=nodes.dtype)
        if constraint_tag.dim() == 1:
            constraint_tag = constraint_tag.unsqueeze(0)
        if constraint_tag.size(0) == 1:
            constraint_tag = constraint_tag.expand(batch_size, -1)
        elif constraint_tag.size(0) != batch_size:
            raise ValueError("constraint tag batch dimension mismatch")

        if guidance is None:
            guidance = nodes.new_ones(1, self.control_guidance_dim)
        else:
            guidance = guidance.to(device=nodes.device, dtype=nodes.dtype)
            if guidance.dim() == 1:
                guidance = guidance.unsqueeze(0)
        if guidance.size(0) == 1:
            guidance = guidance.expand(batch_size, -1)
        elif guidance.size(0) != batch_size:
            raise ValueError("control guidance batch dimension mismatch")

        if constraint_tag.size(-1) != self.control_guidance_dim:
            raise ValueError("problem embedding dimension mismatch")
        if guidance.size(-1) != self.control_guidance_dim:
            raise ValueError("control guidance dimension mismatch")
        return torch.cat((constraint_tag, guidance), dim=-1)


class SideControlBranch(nn.Module):
    """Zero-initialized residual branch controlled by task flags and LLM guidance."""

    def __init__(self, embedding_dim, control_cond_dim, control_hidden_dim):
        super().__init__()
        self.node_proj = nn.Linear(embedding_dim, control_hidden_dim)
        self.cond_proj = nn.Linear(control_cond_dim, control_hidden_dim)
        self.out_proj = nn.Linear(control_hidden_dim, embedding_dim)
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(self, hidden, control_cond, alpha):
        if alpha is None:
            alpha = hidden.new_tensor(1.0)
        control = self.cond_proj(control_cond).unsqueeze(1)
        residual = self.out_proj(F.relu(self.node_proj(hidden) + control))
        return hidden + alpha.to(device=hidden.device, dtype=hidden.dtype) * residual


class ConstraintPrompt(nn.Module):
    """Map the five active-constraint flags to one CaDA prompt token."""

    def __init__(self, embedding_dim):
        super().__init__()
        bottleneck_dim = max(1, embedding_dim // 8)

        input_projection = nn.Linear(5, embedding_dim, bias=False)
        nn.init.uniform_(input_projection.weight)

        self.model = nn.Sequential(
            input_projection,
            nn.LayerNorm(embedding_dim),
            _small_linear(embedding_dim, embedding_dim),
            nn.ReLU(),
            _small_linear(embedding_dim, bottleneck_dim),
            nn.LayerNorm(bottleneck_dim),
            _small_linear(bottleneck_dim, embedding_dim),
        )

    def forward(self, constraint_tag):
        return self.model(constraint_tag).unsqueeze(1)


def _small_linear(input_dim, output_dim):
    """Linear initialization used by the original CaDA prompt network."""
    layer = nn.Linear(input_dim, output_dim)
    nn.init.normal_(layer.weight, std=1e-2)
    nn.init.zeros_(layer.bias)
    return layer


class CaDAEncoderLayer(nn.Module):
    def __init__(self, use_sparse_attention, **model_params):
        super().__init__()
        self.model_params = model_params
        self.use_sparse_attention = use_sparse_attention
        embedding_dim = model_params['embedding_dim']
        head_num = model_params['head_num']
        qkv_dim = model_params['qkv_dim']

        self.Wq = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        self.Wk = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        self.Wv = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        self.multi_head_combine = nn.Linear(head_num * qkv_dim, embedding_dim)

        self.normalization1 = RMSNorm(embedding_dim)
        self.feed_forward = SwiGLU(
            embedding_dim=embedding_dim,
            hidden_dim=model_params['ff_hidden_dim'],
        )
        self.normalization2 = RMSNorm(embedding_dim)

    def forward(self, inputs):
        # inputs.shape: (batch, sequence, embedding)
        head_num = self.model_params['head_num']

        q = reshape_by_heads(self.Wq(inputs), head_num=head_num)
        k = reshape_by_heads(self.Wk(inputs), head_num=head_num)
        v = reshape_by_heads(self.Wv(inputs), head_num=head_num)

        sparse_topk = max(1, inputs.size(1) // 2) if self.use_sparse_attention else None
        out_concat = multi_head_attention(q, k, v, topk=sparse_topk)
        attention_out = self.multi_head_combine(out_concat)
        hidden = self.normalization1(inputs + attention_out)
        return self.normalization2(hidden + self.feed_forward(hidden))


class SwiGLU(nn.Module):
    def __init__(self, embedding_dim, hidden_dim):
        super().__init__()
        self.gate = nn.Linear(embedding_dim, hidden_dim, bias=False)
        self.value = nn.Linear(embedding_dim, hidden_dim, bias=False)
        self.output = nn.Linear(hidden_dim, embedding_dim, bias=False)

    def forward(self, inputs):
        return self.output(F.silu(self.gate(inputs)) * self.value(inputs))


class RMSNorm(nn.Module):
    def __init__(self, embedding_dim, eps=1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(embedding_dim))

    def forward(self, inputs):
        normalized = inputs.float() * torch.rsqrt(
            inputs.float().pow(2).mean(dim=-1, keepdim=True) + self.eps
        )
        return normalized.to(dtype=inputs.dtype) * self.weight


########################################
# DECODER
########################################

class MTL_Decoder(nn.Module):
    def __init__(self, **model_params):
        super().__init__()
        self.model_params = model_params
        embedding_dim = self.model_params['embedding_dim']
        head_num = self.model_params['head_num']
        qkv_dim = self.model_params['qkv_dim']

        # self.Wq_1 = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        # self.Wq_2 = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        self.Wq_last = nn.Linear(embedding_dim + 4, head_num * qkv_dim, bias=False)
        self.Wk = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)
        self.Wv = nn.Linear(embedding_dim, head_num * qkv_dim, bias=False)

        self.multi_head_combine = nn.Linear(head_num * qkv_dim, embedding_dim)

        self.k = None  # saved key, for multi-head attention
        self.v = None  # saved value, for multi-head_attention
        self.single_head_key = None  # saved, for single-head attention
        # self.q1 = None  # saved q1, for multi-head attention
        # self.q2 = None  # saved q2, for multi-head attention

    def set_kv(self, encoded_nodes):
        # encoded_nodes.shape: (batch, problem+1, embedding)
        head_num = self.model_params['head_num']

        self.k = reshape_by_heads(self.Wk(encoded_nodes), head_num=head_num)
        self.v = reshape_by_heads(self.Wv(encoded_nodes), head_num=head_num)
        # shape: (batch, head_num, problem+1, qkv_dim)
        self.single_head_key = encoded_nodes.transpose(1, 2)
        # shape: (batch, embedding, problem+1)

    def set_q1(self, encoded_q1):
        # encoded_q.shape: (batch, n, embedding)  # n can be 1 or pomo
        head_num = self.model_params['head_num']
        self.q1 = reshape_by_heads(self.Wq_1(encoded_q1), head_num=head_num)
        # shape: (batch, head_num, n, qkv_dim)

    def set_q2(self, encoded_q2):
        # encoded_q.shape: (batch, n, embedding)  # n can be 1 or pomo
        head_num = self.model_params['head_num']
        self.q2 = reshape_by_heads(self.Wq_2(encoded_q2), head_num=head_num)
        # shape: (batch, head_num, n, qkv_dim)

    def forward(self, encoded_last_node, attr, ninf_mask):
        # encoded_last_node.shape: (batch, pomo, embedding)
        # attr.shape: (batch, pomo, 4)
        # ninf_mask.shape: (batch, pomo, problem)

        head_num = self.model_params['head_num']

        #  Multi-Head Attention
        #######################################################
        input_cat = torch.cat((encoded_last_node, attr), dim=2)
        # shape = (batch, group, EMBEDDING_DIM+1)

        q_last = reshape_by_heads(self.Wq_last(input_cat), head_num=head_num)
        # shape: (batch, head_num, pomo, qkv_dim)

        # q = self.q1 + self.q2 + q_last
        # # shape: (batch, head_num, pomo, qkv_dim)
        q = q_last
        # shape: (batch, head_num, pomo, qkv_dim)

        out_concat = multi_head_attention(q, self.k, self.v, rank3_ninf_mask=ninf_mask)
        # shape: (batch, pomo, head_num*qkv_dim)

        mh_atten_out = self.multi_head_combine(out_concat)
        # shape: (batch, pomo, embedding)

        #  Single-Head Attention, for probability calculation
        #######################################################
        score = torch.matmul(mh_atten_out, self.single_head_key)
        # shape: (batch, pomo, problem)

        sqrt_embedding_dim = self.model_params['sqrt_embedding_dim']
        logit_clipping = self.model_params['logit_clipping']

        score_scaled = score / sqrt_embedding_dim
        # shape: (batch, pomo, problem)

        score_clipped = logit_clipping * torch.tanh(score_scaled)

        score_masked = score_clipped + ninf_mask

        probs = F.softmax(score_masked, dim=2)
        # shape: (batch, pomo, problem)

        return probs


########################################
# NN SUB CLASS / FUNCTIONS
########################################

def reshape_by_heads(qkv, head_num):
    # q.shape: (batch, n, head_num*key_dim)   : n can be either 1 or PROBLEM_SIZE

    batch_s = qkv.size(0)
    n = qkv.size(1)

    q_reshaped = qkv.reshape(batch_s, n, head_num, -1)
    # shape: (batch, n, head_num, key_dim)

    q_transposed = q_reshaped.transpose(1, 2)
    # shape: (batch, head_num, n, key_dim)

    return q_transposed


def multi_head_attention(q, k, v, rank2_ninf_mask=None, rank3_ninf_mask=None, topk=None):
    # q shape: (batch, head_num, n, key_dim)   : n can be either 1 or PROBLEM_SIZE
    # k,v shape: (batch, head_num, problem, key_dim)
    # rank2_ninf_mask.shape: (batch, problem)
    # rank3_ninf_mask.shape: (batch, group, problem)

    batch_s = q.size(0)
    head_num = q.size(1)
    n = q.size(2)
    key_dim = q.size(3)

    input_s = k.size(2)

    score = torch.matmul(q, k.transpose(2, 3))
    # shape: (batch, head_num, n, problem)

    score_scaled = score / (key_dim ** 0.5)
    if rank2_ninf_mask is not None:
        score_scaled = score_scaled + rank2_ninf_mask[:, None, None, :].expand(batch_s, head_num, n, input_s)
    if rank3_ninf_mask is not None:
        score_scaled = score_scaled + rank3_ninf_mask[:, None, :, :].expand(batch_s, head_num, n, input_s)

    if topk is not None:
        topk = min(max(1, int(topk)), input_s)
        selected = score_scaled.topk(k=topk, dim=-1, largest=True).indices
        keep_mask = torch.zeros_like(score_scaled, dtype=torch.bool)
        keep_mask.scatter_(-1, selected, True)
        score_scaled = score_scaled.masked_fill(~keep_mask, float('-inf'))

    weights = nn.Softmax(dim=3)(score_scaled)
    # shape: (batch, head_num, n, problem)

    out = torch.matmul(weights, v)
    # shape: (batch, head_num, n, key_dim)

    out_transposed = out.transpose(1, 2)
    # shape: (batch, n, head_num, key_dim)

    out_concat = out_transposed.reshape(batch_s, n, head_num * key_dim)
    # shape: (batch, n, head_num*key_dim)

    return out_concat
