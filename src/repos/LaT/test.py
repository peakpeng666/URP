"""Unified evaluation entry point for all five LaT-enabled backbones."""

import argparse
import math
from pathlib import Path
import pprint as pp

from Tester import Tester
from utils import *


ROOT = Path(__file__).resolve().parent
MODEL_TYPES = ("MTL", "MOE", "MOE_LIGHT", "CADA", "RELD")
PROBLEMS = (
    "ALL", "CVRP", "OVRP", "VRPB", "VRPL", "VRPTW", "OVRPTW", "OVRPB",
    "OVRPL", "VRPBL", "VRPBTW", "VRPLTW", "OVRPBL", "OVRPBTW", "OVRPLTW",
    "VRPBLTW", "OVRPBLTW",
)


def _upper(value):
    return value.upper()


def _set_model_defaults(args, parser):
    default_size = 50 if args.model_type in {"MOE", "MOE_LIGHT"} else 100
    if args.problem_size is None:
        args.problem_size = default_size
    if args.pomo_size is None:
        args.pomo_size = args.problem_size
    if args.sqrt_embedding_dim is None:
        args.sqrt_embedding_dim = math.sqrt(args.embedding_dim)
    if args.checkpoint is None:
        candidate = ROOT / "checkpoints" / args.model_type.lower() / "epoch-5000.pt"
        if not candidate.is_file():
            parser.error("--checkpoint is required for {} (no bundled checkpoint found)".format(args.model_type))
        args.checkpoint = str(candidate)


def args2dict(args):
    env_params = {
        "problem_size": args.problem_size,
        "pomo_size": args.pomo_size,
        "device": args.device,
    }
    model_params = {
        "embedding_dim": args.embedding_dim,
        "sqrt_embedding_dim": args.sqrt_embedding_dim,
        "encoder_layer_num": args.encoder_layer_num,
        "decoder_layer_num": args.decoder_layer_num,
        "qkv_dim": args.qkv_dim,
        "head_num": args.head_num,
        "logit_clipping": args.logit_clipping,
        "ff_hidden_dim": args.ff_hidden_dim,
        "num_experts": args.num_experts,
        "eval_type": args.eval_type,
        "norm": args.norm,
        "norm_loc": args.norm_loc,
        "expert_loc": args.expert_loc,
        "problem": None,
        "topk": args.topk,
        "routing_level": args.routing_level,
        "routing_method": args.routing_method,
        "ffidt": args.ffidt,
        "use_control_branch": args.use_control_branch,
        "control_guidance_dim": args.control_guidance_dim,
        "control_hidden_dim": args.control_hidden_dim,
        "control_guidance": args.control_guidance,
        "control_init_alpha": args.control_init_alpha,
        "control_injection": args.control_injection,
        "control_ablation": args.control_ablation,
        "device": args.device,
    }
    tester_params = {
        "checkpoint": args.checkpoint,
        "test_episodes": args.test_episodes,
        "test_batch_size": args.test_batch_size,
        "sample_size": args.sample_size,
        "aug_factor": args.aug_factor,
        "aug_batch_size": args.aug_batch_size,
        "test_set_path": args.test_set_path,
        "test_set_opt_sol_path": args.test_set_opt_sol_path,
        "fine_tune_episodes": args.fine_tune_episodes,
        "fine_tune_epochs": args.fine_tune_epochs,
        "fine_tune_batch_size": args.fine_tune_batch_size,
        "fine_tune_aug_factor": args.fine_tune_aug_factor,
        "lr": args.lr,
        "weight_decay": args.weight_decay,
    }
    return env_params, model_params, tester_params


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified LaT evaluation: MTL, MOE, MOE_LIGHT, CADA, or RELD"
    )
    parser.add_argument("--model_type", "--model-type", type=_upper, default="MTL", choices=MODEL_TYPES)
    parser.add_argument("--problem", default="ALL", choices=PROBLEMS)
    parser.add_argument("--problem_size", type=int, default=None)
    parser.add_argument("--pomo_size", type=int, default=None)
    parser.add_argument("--embedding_dim", type=int, default=128)
    parser.add_argument("--sqrt_embedding_dim", type=float, default=None)
    parser.add_argument("--encoder_layer_num", type=int, default=6)
    parser.add_argument("--decoder_layer_num", type=int, default=1)
    parser.add_argument("--qkv_dim", type=int, default=16)
    parser.add_argument("--head_num", type=int, default=8)
    parser.add_argument("--logit_clipping", type=float, default=10)
    parser.add_argument("--ff_hidden_dim", type=int, default=512)
    parser.add_argument("--num_experts", type=int, default=4)
    parser.add_argument("--eval_type", default="argmax", choices=("argmax", "softmax"))
    parser.add_argument("--norm", default="instance", choices=("batch", "batch_no_track", "instance", "layer", "rezero", "none"))
    parser.add_argument("--norm_loc", default="norm_last", choices=("norm_first", "norm_last"))
    parser.add_argument("--topk", type=int, default=2)
    parser.add_argument("--expert_loc", nargs="+", default=["Enc0", "Enc1", "Enc2", "Enc3", "Enc4", "Enc5", "Dec"])
    parser.add_argument("--routing_level", default="node", choices=("node", "instance", "problem"))
    parser.add_argument("--routing_method", default="input_choice", choices=("input_choice", "expert_choice", "soft_moe", "random"))

    ffidt = parser.add_mutually_exclusive_group()
    ffidt.add_argument("--ffidt", dest="ffidt", action="store_true")
    ffidt.add_argument("--no_ffidt", dest="ffidt", action="store_false")
    parser.set_defaults(ffidt=True)
    parser.add_argument("--use_control_branch", action="store_true")
    parser.add_argument("--control_guidance_dim", type=int, default=5)
    parser.add_argument("--control_hidden_dim", type=int, default=128)
    parser.add_argument("--control_guidance", type=float, nargs="+", default=[1.0] * 5)
    parser.add_argument("--control_init_alpha", type=float, default=0.02)
    parser.add_argument("--control_injection", default="encoder_all", choices=("encoder_all", "input_prompt", "encoder_last", "decoder_context"))
    parser.add_argument("--control_ablation", default="full", choices=("full", "no_llm_guidance", "no_constraint_guidance", "random_guidance"))

    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--test_episodes", type=int, default=1000)
    parser.add_argument("--test_batch_size", type=int, default=1000)
    parser.add_argument("--sample_size", type=int, default=10)
    parser.add_argument("--aug_factor", type=int, default=8, choices=(1, 8))
    parser.add_argument("--aug_batch_size", type=int, default=100)
    parser.add_argument("--test_set_path", default=None)
    parser.add_argument("--test_set_opt_sol_path", default=None)
    parser.add_argument("--fine_tune_epochs", type=int, default=0)
    parser.add_argument("--fine_tune_episodes", type=int, default=10000)
    parser.add_argument("--fine_tune_batch_size", type=int, default=128)
    parser.add_argument("--fine_tune_aug_factor", type=int, default=1, choices=(1, 8))
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--no_cuda", action="store_true")
    parser.add_argument("--gpu_id", type=int, default=0)
    parser.add_argument("--occ_gpu", type=float, default=0.0)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    _set_model_defaults(args, parser)
    if args.pomo_size > args.problem_size:
        parser.error("--pomo_size must not exceed --problem_size")
    if len(args.control_guidance) != args.control_guidance_dim:
        parser.error("--control_guidance length must equal --control_guidance_dim")
    if args.control_guidance_dim != 5:
        parser.error("the unified [C,O,B,L,TW] guidance must have dimension 5")
    if not all(math.isfinite(value) for value in args.control_guidance):
        parser.error("--control_guidance values must be finite")
    if args.control_hidden_dim <= 0:
        parser.error("--control_hidden_dim must be positive")
    if not math.isfinite(args.control_init_alpha):
        parser.error("--control_init_alpha must be finite")

    seed_everything(args.seed)
    if args.aug_factor != 1:
        args.test_batch_size = args.aug_batch_size
    if not args.no_cuda and torch.cuda.is_available():
        occumpy_mem(args) if args.occ_gpu else None
        args.device = torch.device("cuda", args.gpu_id)
        torch.cuda.set_device(args.gpu_id)
        torch.set_default_tensor_type("torch.cuda.FloatTensor")
    else:
        args.device = torch.device("cpu")
        torch.set_default_tensor_type("torch.FloatTensor")

    env_params, model_params, tester_params = args2dict(args)
    pp.pprint(vars(args))
    print(">> Unified model: {}".format(args.model_type))
    print(">> Device: {}".format(args.device))
    tester = Tester(args, env_params, model_params, tester_params)
    tester.run()
    print(">> Finished {} evaluation.".format(args.model_type))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
