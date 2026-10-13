"""Generate datasets using the unified environment package."""

import argparse
import os
import pprint as pp

from utils import *


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate unified LaT datasets")
    parser.add_argument("--problem", default="ALL", choices=("ALL", "CVRP", "OVRP", "VRPB", "VRPL", "VRPTW", "OVRPTW", "OVRPB", "OVRPL", "VRPBL", "VRPBTW", "VRPLTW", "OVRPBL", "OVRPBTW", "OVRPLTW", "VRPBLTW", "OVRPBLTW"))
    parser.add_argument("--problem_size", type=int, default=50, choices=(20, 50, 100, 200))
    parser.add_argument("--pomo_size", type=int, default=None)
    parser.add_argument("--num_samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--dir", default="./data")
    parser.add_argument("--no_cuda", action="store_true")
    parser.add_argument("--gpu_id", type=int, default=0)
    args = parser.parse_args(argv)
    if args.pomo_size is None:
        args.pomo_size = args.problem_size
    seed_everything(args.seed)
    if not args.no_cuda and torch.cuda.is_available():
        args.device = torch.device("cuda", args.gpu_id)
        torch.cuda.set_device(args.gpu_id)
        torch.set_default_tensor_type("torch.cuda.FloatTensor")
    else:
        args.device = torch.device("cpu")
        torch.set_default_tensor_type("torch.FloatTensor")
    pp.pprint(vars(args))

    env_params = {"problem_size": args.problem_size, "pomo_size": args.pomo_size, "device": args.device}
    for env_class in get_env(args.problem):
        env = env_class(**env_params)
        path = os.path.join(args.dir, env.problem, "{}{}_uniform.pkl".format(env.problem.lower(), args.problem_size))
        env.generate_dataset(args.num_samples, args.problem_size, path)
        env.load_dataset(path, num_samples=args.num_samples, disable_print=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
