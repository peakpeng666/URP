import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from torch.optim import Adam as Optimizer
from torch.optim.lr_scheduler import MultiStepLR as Scheduler

from utils import *


VAL_PROBLEMS = ["CVRP", "OVRP", "VRPB", "VRPL", "VRPTW", "OVRPTW",
                "OVRPB", "OVRPL", "VRPBL", "VRPBTW", "VRPLTW", "OVRPBL",
                "OVRPBTW", "OVRPLTW", "VRPBLTW", "OVRPBLTW"]

CONTROL_BITS = {
    "CVRP": [1, 0, 0, 0, 0],
    "OVRP": [1, 1, 0, 0, 0],
    "VRPB": [1, 0, 1, 0, 0],
    "VRPL": [1, 0, 0, 1, 0],
    "VRPTW": [1, 0, 0, 0, 1],
    "OVRPTW": [1, 1, 0, 0, 1],
    "OVRPB": [1, 1, 1, 0, 0],
    "OVRPL": [1, 1, 0, 1, 0],
    "VRPBL": [1, 0, 1, 1, 0],
    "VRPBTW": [1, 0, 1, 0, 1],
    "VRPLTW": [1, 0, 0, 1, 1],
    "OVRPBL": [1, 1, 1, 1, 0],
    "OVRPBTW": [1, 1, 1, 0, 1],
    "OVRPLTW": [1, 1, 0, 1, 1],
    "VRPBLTW": [1, 0, 1, 1, 1],
    "OVRPBLTW": [1, 1, 1, 1, 1],
}

LLM_CONTROL_DEFAULTS = {
    "model": "glm-5.1",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key_env": "LLM_ENV_DESIGNER_API_KEY",
    "history_limit": 5,
    "timeout": 600,
    "retries": 3,
}


def load_checkpoint(checkpoint_path, device):
    """Load both older and newer PyTorch checkpoints explicitly and safely."""
    try:
        return torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        return torch.load(checkpoint_path, map_location=device)


def load_model_state_compat(model, state_dict, allow_new_control=False):
    """Allow only newly introduced zero-initialized control parameters to be absent."""
    incompatible = model.load_state_dict(state_dict, strict=False)
    missing = list(incompatible.missing_keys)
    unexpected = list(incompatible.unexpected_keys)
    if allow_new_control:
        allowed_missing = [
            key for key in missing
            if key in {"control_guidance", "control_alpha"} or key.startswith("encoder.control_layers.")
        ]
        missing = [key for key in missing if key not in allowed_missing]
        if allowed_missing:
            print(">> Initialized new LLM control parameters: {} tensors".format(len(allowed_missing)))
    if missing or unexpected:
        raise RuntimeError(
            "Checkpoint/model mismatch. Missing keys: {}; unexpected keys: {}".format(missing, unexpected)
        )


class Trainer:
    def __init__(self, args, env_params, model_params, optimizer_params, trainer_params):
        # save arguments
        self.args = args
        self.env_params = env_params
        self.model_params = model_params
        self.optimizer_params = optimizer_params
        self.trainer_params = trainer_params

        self.device = args.device
        self.log_path = args.log_path
        self.result_log = {"val_score": [], "val_gap": []}
        self.control_history = []

        # Main Components
        self.envs = get_env(self.args.problem)  # a list of envs classes (different problems), remember to initialize it!
        self.model = get_model(self.args.model_type)(**self.model_params)
        self.optimizer = Optimizer(self.model.parameters(), **self.optimizer_params['optimizer'])
        self.scheduler = Scheduler(self.optimizer, **self.optimizer_params['scheduler'])
        num_param(self.model)

        # Restore
        self.start_epoch = 1
        if args.checkpoint is not None:
            checkpoint_fullname = args.checkpoint
            checkpoint = load_checkpoint(checkpoint_fullname, self.device)
            validate_checkpoint_model_type(checkpoint, self.args.model_type, legacy_model_types=("MTL",))
            load_model_state_compat(
                self.model,
                checkpoint['model_state_dict'],
                allow_new_control=self.model_params.get('use_control_branch', False),
            )
            self.start_epoch = 1 + checkpoint['epoch']
            try:
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            except ValueError as exception:
                print(">> Optimizer state skipped: {}. This is expected when adding the control branch to an old ReLD checkpoint.".format(exception))
            self.scheduler.last_epoch = checkpoint['epoch'] - 1
            self.result_log = checkpoint.get('result_log', self.result_log)
            self.control_history = checkpoint.get('control_history', [])
            print(">> Checkpoint (Epoch: {}) Loaded!".format(checkpoint['epoch']))

        # utility
        self.time_estimator = TimeEstimator()

    def run(self):
        self.time_estimator.reset(self.start_epoch)
        for epoch in range(self.start_epoch, self.trainer_params['epochs']+1):
            print('=================================================================')
            self._maybe_update_control_guidance(epoch)

            # Train
            train_score, train_loss = self._train_one_epoch(epoch)
            self.scheduler.step()

            # Logs & Checkpoint
            elapsed_time_str, remain_time_str = self.time_estimator.get_est_string(epoch, self.trainer_params['epochs'])
            print("Epoch {:3d}/{:3d}: Time Est.: Elapsed[{}], Remain[{}]".format(epoch, self.trainer_params['epochs'], elapsed_time_str, remain_time_str))

            all_done = (epoch == self.trainer_params['epochs'])
            model_save_interval = self.trainer_params['model_save_interval']
            validation_interval = self.trainer_params['validation_interval']

            # MTL Validation & save latest images
            if epoch == 1 or (epoch % validation_interval == 0):
                val_problems = VAL_PROBLEMS
                val_episodes, problem_size = 1000, self.env_params['problem_size']
                dir = [os.path.join("./data", prob) for prob in val_problems]
                paths = ["{}{}_uniform.pkl".format(prob.lower(), problem_size) for prob in val_problems]
                val_envs = [get_env(prob)[0] for prob in val_problems]
                for i, path in enumerate(paths):
                    # if no optimal solution provided, set compute_gap to False
                    score, gap = self._val_and_stat(dir[i], path, val_envs[i](**{"problem_size": problem_size, "pomo_size": problem_size, "device": self.device}), batch_size=500, val_episodes=val_episodes, compute_gap=True)
                    self.result_log["val_score"].append(score)
                    self.result_log["val_gap"].append(gap)

                score_image_prefix = '{}/latest_val_score'.format(self.log_path)
                gap_image_prefix = '{}/latest_val_gap'.format(self.log_path)
                x, y1, y2, label = [], [], [], []
                for i, path in enumerate(paths):
                    y1.append([r for j, r in enumerate(self.result_log["val_score"]) if j % len(paths) == i])
                    y2.append([r for j, r in enumerate(self.result_log["val_gap"]) if j % len(paths) == i])
                    x.append([j * validation_interval for j in range(len(y1[-1]))])
                    label.append(val_problems[i])
                show(x, y1, label, title="Validation", xdes="Epoch", ydes="Score", path="{}.pdf".format(score_image_prefix))
                show(x, y2, label, title="Validation", xdes="Epoch", ydes="Opt. Gap (%)", path="{}.pdf".format(gap_image_prefix))

            if all_done or (epoch % model_save_interval == 0):
                print("Saving trained_model")
                checkpoint_dict = {
                    'epoch': epoch,
                    'problem': self.args.problem,
                    'model_type': self.args.model_type,
                    'model_params': self.model_params,
                    'trainer_params': self.trainer_params,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'scheduler_state_dict': self.scheduler.state_dict(),
                    'result_log': self.result_log,
                    'control_history': self.control_history
                }
                torch.save(checkpoint_dict, '{}/epoch-{}.pt'.format(self.log_path, epoch))

    def _maybe_update_control_guidance(self, epoch):
        if not self.model_params.get('use_control_branch', False):
            return
        if not hasattr(self.model, 'set_control_guidance'):
            return
        interval = max(1, int(self.trainer_params.get('control_update_interval', 500)))
        if epoch != self.start_epoch and (epoch - 1) % interval != 0:
            return

        guidance, source, reason = self._build_control_guidance()
        self.model.set_control_guidance(guidance=guidance)
        alpha = self._current_control_alpha()
        self._record_control_update(epoch, alpha, guidance, source, reason)
        print(">> ReLD LaT Control Update @ epoch {} [{}]: learnable_alpha={:.4f}, guidance={}, reason={}".format(
            epoch, source, alpha, [round(v, 4) for v in guidance], reason))

    def _current_control_alpha(self):
        alpha = getattr(self.model, 'control_alpha', None)
        return 0.0 if alpha is None else float(alpha.detach().item())

    def _build_control_guidance(self):
        base = list(self.model_params.get('control_guidance', [1., 1., 1., 1., 1.]))
        if len(self.result_log['val_gap']) < len(VAL_PROBLEMS):
            return base, 'base', 'not enough validation statistics yet'

        if self.trainer_params.get('llm_control', False):
            guidance, reason = self._try_build_llm_control_guidance(base)
            if guidance is not None:
                return guidance, 'llm', reason

        return (
            self._build_stat_control_guidance(base),
            'stat',
            'LLM disabled or unavailable; used gap-weighted constraint focus',
        )

    def _build_stat_control_guidance(self, base):
        latest_gaps = self.result_log['val_gap'][-len(VAL_PROBLEMS):]
        focus = [0.0 for _ in base]
        for problem, gap in zip(VAL_PROBLEMS, latest_gaps):
            gap = float(gap)
            gap = max(gap, 0.0) if math.isfinite(gap) else 0.0
            for index, bit in enumerate(CONTROL_BITS[problem]):
                focus[index] += gap * bit

        focus_max = max(focus)
        if focus_max > 0:
            focus = [value / focus_max for value in focus]
        stat_mix = min(max(float(self.trainer_params.get('control_stat_mix', 0.5)), 0.0), 1.0)
        return [
            (1.0 - stat_mix) * base_value + stat_mix * (1.0 + focus_value)
            for base_value, focus_value in zip(base, focus)
        ]

    def _try_build_llm_control_guidance(self, base):
        try:
            response = self._call_llm_control(self._build_llm_control_payload(base))
            guidance = response.get('guidance')
            if not isinstance(guidance, list) or len(guidance) != len(base):
                raise ValueError('LLM response must contain guidance with {} values'.format(len(base)))
            min_value = float(self.trainer_params.get('llm_control_min', 0.5))
            max_value = float(self.trainer_params.get('llm_control_max', 2.0))
            if not math.isfinite(min_value) or not math.isfinite(max_value):
                raise ValueError('LLM guidance bounds must be finite')
            if min_value > max_value:
                raise ValueError('llm_control_min must not exceed llm_control_max')
            parsed = [float(value) for value in guidance]
            if not all(math.isfinite(value) for value in parsed):
                raise ValueError('LLM guidance must contain finite numbers')
            guidance = [min(max(value, min_value), max_value) for value in parsed]
            reason = str(response.get('reason', 'LLM returned semantic guidance'))
            return guidance, reason
        except Exception as exception:
            print(">> LLM control unavailable: {}. Falling back to statistical guidance.".format(exception))
            return None, None

    def _build_llm_control_payload(self, base):
        problem_count = len(VAL_PROBLEMS)
        latest_scores = self.result_log['val_score'][-problem_count:]
        latest_gaps = self.result_log['val_gap'][-problem_count:]
        history_limit = max(1, int(self.trainer_params.get(
            'llm_gap_history_limit', LLM_CONTROL_DEFAULTS['history_limit']
        )))
        complete_rounds = min(
            len(self.result_log['val_score']) // problem_count,
            len(self.result_log['val_gap']) // problem_count,
        )
        history_rounds = min(history_limit, complete_rounds)
        gap_history = []
        score_history = []
        for round_index in range(history_rounds, 0, -1):
            start = -round_index * problem_count
            end = None if round_index == 1 else -(round_index - 1) * problem_count
            gap_history.append(self.result_log['val_gap'][start:end])
            score_history.append(self.result_log['val_score'][start:end])

        tasks = []
        guidance_names = ['C', 'O', 'B', 'L', 'TW']
        for index, problem in enumerate(VAL_PROBLEMS):
            task_gap_history = [float(round_gaps[index]) for round_gaps in gap_history]
            task_score_history = [float(round_scores[index]) for round_scores in score_history]
            gap_delta = None if len(task_gap_history) < 2 else task_gap_history[-1] - task_gap_history[-2]
            tasks.append({
                'problem': problem,
                'constraints': dict(zip(guidance_names, CONTROL_BITS[problem])),
                'score': float(latest_scores[index]),
                'gap': float(latest_gaps[index]),
                'gap_delta': gap_delta,
                'score_history': task_score_history,
                'gap_history': task_gap_history,
            })

        current_guidance = base
        if hasattr(self.model, 'control_guidance'):
            current_guidance = self.model.control_guidance.detach().flatten().cpu().tolist()
        return {
            'guidance_names': guidance_names,
            'base_guidance': base,
            'current_guidance': current_guidance,
            'tasks': tasks,
            'instruction': 'Return conservative values; a higher value strengthens that constraint side branch.',
        }

    def _call_llm_control(self, payload):
        base_url = self.trainer_params.get(
            'llm_control_base_url', LLM_CONTROL_DEFAULTS['base_url']
        ).rstrip('/')
        model = self.trainer_params.get('llm_control_model', LLM_CONTROL_DEFAULTS['model'])
        api_key_env = self.trainer_params.get(
            'llm_control_api_key_env', LLM_CONTROL_DEFAULTS['api_key_env']
        )
        api_key = os.environ.get('LLM_CONTROL_API_KEY') or os.environ.get(api_key_env)
        if not base_url:
            raise ValueError('empty LLM control base URL')
        if not model:
            raise ValueError('empty LLM control model')
        if api_key is None and 'localhost' not in base_url and '127.0.0.1' not in base_url:
            raise ValueError('missing API key; set LLM_CONTROL_API_KEY or {}'.format(api_key_env))

        messages = [
            {
                'role': 'system',
                'content': (
                    "You are an LLM trainer for a multi-task vehicle routing ReLD model. "
                    "Analyze validation score/gap and return strict JSON only. "
                    "The guidance vector order is [C, O, B, L, TW], meaning capacity, open route, "
                    "backhaul, route length, and time window. Values must be conservative floats."
                ),
            },
            {
                'role': 'user',
                'content': (
                    'Return JSON with exactly two keys: guidance (5 floats) and reason (short string). '
                    'Each guidance value must be in [{}, {}].\n{}'
                ).format(
                    self.trainer_params.get('llm_control_min', 0.5),
                    self.trainer_params.get('llm_control_max', 2.0),
                    json.dumps(payload, ensure_ascii=False),
                ),
            },
        ]
        request_body = {
            'model': model,
            'messages': messages,
            'temperature': float(self.trainer_params.get('llm_control_temperature', 0.0)),
        }
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = 'Bearer {}'.format(api_key)
        request = urllib.request.Request(
            '{}/chat/completions'.format(base_url),
            data=json.dumps(request_body).encode('utf-8'),
            headers=headers,
            method='POST',
        )

        timeout = float(self.trainer_params.get('llm_control_timeout', LLM_CONTROL_DEFAULTS['timeout']))
        retries = max(1, int(self.trainer_params.get(
            'llm_control_retries', LLM_CONTROL_DEFAULTS['retries']
        )))
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read().decode('utf-8')
                break
            except urllib.error.HTTPError as exception:
                error_body = exception.read().decode('utf-8', errors='replace')
                last_error = RuntimeError('LLM HTTP {}: {}'.format(exception.code, error_body[:500]))
            except (urllib.error.URLError, TimeoutError) as exception:
                last_error = exception
            if attempt < retries:
                time.sleep(min(2 ** (attempt - 1), 10))
        else:
            raise last_error

        data = json.loads(body)
        content = data['choices'][0]['message']['content']
        return self._parse_llm_json(content)

    @staticmethod
    def _parse_llm_json(content):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, flags=re.S)
            if match is None:
                raise
            return json.loads(match.group(0))

    def _record_control_update(self, epoch, alpha, guidance, source, reason):
        record = {
            'epoch': int(epoch),
            'alpha': float(alpha),
            'guidance': [float(value) for value in guidance],
            'source': source,
            'reason': reason,
        }
        self.control_history.append(record)
        path = os.path.join(self.log_path, 'control_updates.jsonl')
        with open(path, 'a', encoding='utf-8') as file:
            file.write(json.dumps(record, ensure_ascii=False) + '\n')

    def _train_one_epoch(self, epoch):
        episode = 0
        score_AM, loss_AM = AverageMeter(), AverageMeter()
        train_num_episode = self.trainer_params['train_episodes']

        while episode < train_num_episode:
            remaining = train_num_episode - episode
            batch_size = min(self.trainer_params['train_batch_size'], remaining)

            env = random.sample(self.envs, 1)[0](**self.env_params)
            data = env.get_random_problems(batch_size, self.env_params["problem_size"])
            avg_score, avg_loss = self._train_one_batch(data, env)
            # print(avg_score, avg_loss)

            score_AM.update(avg_score, batch_size)
            loss_AM.update(avg_loss, batch_size)
            episode += batch_size

        # Log Once, for each epoch
        print('Epoch {:3d}: Train ({:3.0f}%)  Score: {:.4f},  Loss: {:.4f}'.format(epoch, 100. * episode / train_num_episode, score_AM.avg, loss_AM.avg))

        return score_AM.avg, loss_AM.avg

    def _train_one_batch(self, data, env):
        self.model.train()
        self.model.set_eval_type(self.model_params["eval_type"])
        batch_size = data.size(0) if isinstance(data, torch.Tensor) else data[-1].size(0)
        env.load_problems(batch_size, problems=data, aug_factor=1)
        reset_state, _, _ = env.reset()
        self.model.pre_forward(reset_state)
        prob_list = torch.zeros(size=(batch_size, env.pomo_size, 0))
        # shape: (batch, pomo, 0~problem)

        # POMO Rollout
        state, reward, done = env.pre_step()
        # print("{}\n".format(state.PROBLEM))
        while not done:
            selected, prob = self.model(state)
            # shape: (batch, pomo)
            state, reward, done = env.step(selected)
            prob_list = torch.cat((prob_list, prob[:, :, None]), dim=2)

        # Loss
        advantage = reward - reward.float().mean(dim=1, keepdims=True)  # (batch, pomo)
        log_prob = prob_list.log().sum(dim=2)
        loss = -advantage * log_prob  # Minus Sign: To Increase REWARD
        loss_mean = loss.mean()
        max_pomo_reward, _ = reward.max(dim=1)  # get best results from pomo
        score_mean = -max_pomo_reward.float().mean()  # negative sign to make positive value

        if hasattr(self.model, "aux_loss"):
            loss_mean = loss_mean + self.model.aux_loss  # add aux(moe)_loss for load balancing (default coefficient: 1e-2)

        # Step & Return
        self.model.zero_grad()
        loss_mean.backward()
        self.optimizer.step()

        return score_mean.item(), loss_mean.item()

    def _val_one_batch(self, data, env, aug_factor=1, eval_type="argmax"):
        self.model.eval()
        self.model.set_eval_type(eval_type)
        batch_size = data.size(0) if isinstance(data, torch.Tensor) else data[-1].size(0)
        with torch.no_grad():
            env.load_problems(batch_size, problems=data, aug_factor=aug_factor)
            reset_state, _, _ = env.reset()
            self.model.pre_forward(reset_state)
            state, reward, done = env.pre_step()
            while not done:
                selected, _ = self.model(state)
                # shape: (batch, pomo)
                state, reward, done = env.step(selected)

        # Return
        aug_reward = reward.reshape(aug_factor, batch_size, env.pomo_size)
        # shape: (augmentation, batch, pomo)
        max_pomo_reward, _ = aug_reward.max(dim=2)  # get best results from pomo
        no_aug_score = -max_pomo_reward[0, :].float()  # negative sign to make positive value
        max_aug_pomo_reward, _ = max_pomo_reward.max(dim=0)  # get best results from augmentation
        aug_score = -max_aug_pomo_reward.float()  # negative sign to make positive value

        return no_aug_score, aug_score

    def _val_and_stat(self, dir, val_path, env, batch_size=500, val_episodes=1000, compute_gap=False):
        no_aug_score_list, aug_score_list, no_aug_gap_list, aug_gap_list = [], [], [], []
        episode, no_aug_score, aug_score = 0, torch.zeros(0).to(self.device), torch.zeros(0).to(self.device)

        while episode < val_episodes:
            remaining = val_episodes - episode
            bs = min(batch_size, remaining)
            data = env.load_dataset(os.path.join(dir, val_path), offset=episode, num_samples=bs)
            no_aug, aug = self._val_one_batch(data, env, aug_factor=8, eval_type="argmax")
            no_aug_score = torch.cat((no_aug_score, no_aug), dim=0)
            aug_score = torch.cat((aug_score, aug), dim=0)
            episode += bs

        no_aug_score_list.append(round(no_aug_score.mean().item(), 4))
        aug_score_list.append(round(aug_score.mean().item(), 4))

        if compute_gap:
            opt_sol = load_dataset(get_opt_sol_path(dir, env.problem, data[1].size(1)), disable_print=True)[: val_episodes]
            opt_sol = [i[0] for i in opt_sol]
            gap = [(no_aug_score[j].item() - opt_sol[j]) / opt_sol[j] * 100 for j in range(val_episodes)]
            no_aug_gap_list.append(round(sum(gap) / len(gap), 4))
            gap = [(aug_score[j].item() - opt_sol[j]) / opt_sol[j] * 100 for j in range(val_episodes)]
            aug_gap_list.append(round(sum(gap) / len(gap), 4))
            print(">> Val Score on {}: NO_AUG_Score: {}, NO_AUG_Gap: {}% --> AUG_Score: {}, AUG_Gap: {}%".format(val_path, no_aug_score_list, no_aug_gap_list, aug_score_list, aug_gap_list))
            return aug_score_list[0], aug_gap_list[0]
        else:
            print(">> Val Score on {}: NO_AUG_Score: {}, --> AUG_Score: {}".format(val_path, no_aug_score_list, aug_score_list))
            return aug_score_list[0], 0
