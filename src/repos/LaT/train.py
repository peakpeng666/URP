"""Unified training entry point for all five LaT-enabled backbones."""

import argparse
import math
import os
import pprint as pp
from datetime import datetime

import pytz

from Trainer import Trainer
from utils import *


MODEL_TYPES = ("MTL", "MOE", "MOE_LIGHT", "CADA", "RELD")
PROBLEMS = (
    "Train_ALL", "CVRP", "OVRP", "VRPB", "VRPL", "VRPTW", "OVRPTW",
    "OVRPB", "OVRPL", "VRPBL", "VRPBTW", "VRPLTW", "OVRPBL",
    "OVRPBTW", "OVRPLTW", "VRPBLTW", "OVRPBLTW",
)


def _upper(value):
    return value.upper()


def _set_model_defaults(args):
    default_size = 50 if args.model_type in {"MOE", "MOE_LIGHT"} else 100
    if args.problem_size is None:
        args.problem_size = default_size
    if args.pomo_size is None:
        args.pomo_size = args.problem_size
    if args.sqrt_embedding_dim is None:
        args.sqrt_embedding_dim = math.sqrt(args.embedding_dim)
    if args.log_dir is None:
        args.log_dir = os.path.join("results", args.model_type.lower())


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
        "problem": args.problem,
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
    optimizer_params = {
        "optimizer": {"lr": args.lr, "weight_decay": args.weight_decay},
        "scheduler": {"milestones": args.milestones, "gamma": args.gamma},
    }
    trainer_params = {
        "epochs": args.epochs,
        "train_episodes": args.train_episodes,
        "train_batch_size": args.train_batch_size,
        "validation_interval": args.validation_interval,
        "model_save_interval": args.model_save_interval,
        "checkpoint": args.checkpoint,
        "control_update_interval": args.control_update_interval,
        "control_max_alpha": args.control_max_alpha,
        "control_stat_mix": args.control_stat_mix,
        "llm_control": args.llm_control,
        "llm_control_model": args.llm_control_model,
        "llm_control_base_url": args.llm_control_base_url,
        "llm_control_api_key_env": args.llm_control_api_key_env,
        "llm_gap_history_limit": args.llm_gap_history_limit,
        "llm_control_timeout": args.llm_control_timeout,
        "llm_control_retries": args.llm_control_retries,
        "llm_control_temperature": args.llm_control_temperature,
        "llm_control_min": args.llm_control_min,
        "llm_control_max": args.llm_control_max,
    }
    return env_params, model_params, optimizer_params, trainer_params


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified LaT training: MTL, MOE, MOE_LIGHT, CADA, or RELD"
    )
    parser.add_argument("--model_type", "--model-type", type=_upper, default="MTL", choices=MODEL_TYPES)
    parser.add_argument("--problem", default="Train_ALL", choices=PROBLEMS)
    parser.add_argument("--problem_size", "--problem-size", type=int, default=None)
    parser.add_argument("--pomo_size", "--pomo-size", type=int, default=None)

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

    control = parser.add_mutually_exclusive_group()
    control.add_argument("--use_control_branch", dest="use_control_branch", action="store_true")
    control.add_argument("--no_control_branch", dest="use_control_branch", action="store_false")
    parser.set_defaults(use_control_branch=True)
    parser.add_argument("--control_guidance_dim", type=int, default=5)
    parser.add_argument("--control_hidden_dim", type=int, default=128)
    parser.add_argument("--control_guidance", type=float, nargs="+", default=[1.0] * 5)
    parser.add_argument("--control_init_alpha", type=float, default=0.02)
    parser.add_argument(
        "--control_injection",
        default="encoder_all",
        choices=("encoder_all", "input_prompt", "encoder_last", "decoder_context"),
        help="MTL injection location; other backbones keep their original fixed location",
    )
    parser.add_argument(
        "--control_ablation",
        default="full",
        choices=("full", "no_llm_guidance", "no_constraint_guidance", "random_guidance"),
        help="MTL component ablation; ignored by backbones that do not implement it",
    )

    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--milestones", type=int, nargs="+", default=[4501])
    parser.add_argument("--gamma", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=5000)
    parser.add_argument("--train_episodes", type=int, default=20000)
    parser.add_argument("--train_batch_size", type=int, default=128)
    parser.add_argument("--validation_interval", type=int, default=50)
    parser.add_argument("--model_save_interval", type=int, default=2500)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--control_update_interval", type=int, default=500)
    parser.add_argument(
        "--control_max_alpha",
        type=float,
        default=0.2,
        help="deprecated compatibility option; control_alpha is learned",
    )
    parser.add_argument("--control_stat_mix", type=float, default=0.5)

    llm = parser.add_mutually_exclusive_group()
    llm.add_argument("--llm_control", dest="llm_control", action="store_true")
    llm.add_argument("--no_llm_control", dest="llm_control", action="store_false")
    parser.set_defaults(llm_control=True)
    parser.add_argument("--llm_control_model", default="glm-5.1")
    parser.add_argument("--llm_control_base_url", default="https://open.bigmodel.cn/api/paas/v4")
    parser.add_argument("--llm_control_api_key_env", default="LLM_ENV_DESIGNER_API_KEY")
    parser.add_argument("--llm_gap_history_limit", type=int, default=5)
    parser.add_argument("--llm_control_timeout", type=float, default=600)
    parser.add_argument("--llm_control_retries", type=int, default=3)
    parser.add_argument("--llm_control_temperature", type=float, default=0.0)
    parser.add_argument("--llm_control_min", type=float, default=0.5)
    parser.add_argument("--llm_control_max", type=float, default=2.0)

    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--log_dir", default=None)
    parser.add_argument("--no_cuda", action="store_true")
    parser.add_argument("--gpu_id", type=int, default=0)
    parser.add_argument("--occ_gpu", type=float, default=0.0)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    _set_model_defaults(args)
    if args.problem_size not in (50, 100):
        parser.error(
            "LaT training requires --problem_size 50 or 100 because cross-task "
            "reference-gap validation is defined only for these sizes"
        )
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
    if args.llm_control and not args.use_control_branch:
        parser.error("--llm_control requires --use_control_branch")
    if not math.isfinite(args.control_stat_mix) or not 0.0 <= args.control_stat_mix <= 1.0:
        parser.error("--control_stat_mix must be in [0,1]")
    if not math.isfinite(args.llm_control_min) or not math.isfinite(args.llm_control_max):
        parser.error("--llm_control_min and --llm_control_max must be finite")
    if args.llm_control_min > args.llm_control_max:
        parser.error("--llm_control_min must not exceed --llm_control_max")

    seed_everything(args.seed)
    torch.set_printoptions(threshold=1000000)
    if not args.no_cuda and torch.cuda.is_available():
        occumpy_mem(args) if args.occ_gpu else None
        args.device = torch.device("cuda", args.gpu_id)
        torch.cuda.set_device(args.gpu_id)
        torch.set_default_tensor_type("torch.cuda.FloatTensor")
    else:
        args.device = torch.device("cpu")
        torch.set_default_tensor_type("torch.FloatTensor")

    process_start_time = datetime.now(pytz.timezone("Asia/Singapore"))
    args.log_path = os.path.join(args.log_dir, process_start_time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(args.log_path, exist_ok=True)
    env_params, model_params, optimizer_params, trainer_params = args2dict(args)

    pp.pprint(vars(args))
    print(">> Unified model: {}".format(args.model_type))
    print(">> Log Path: {}".format(args.log_path))
    print(">> Device: {}".format(args.device))
    trainer = Trainer(args, env_params, model_params, optimizer_params, trainer_params)
    trainer.run()
    print(">> Finished {} training.".format(args.model_type))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
