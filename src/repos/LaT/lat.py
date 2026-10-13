#!/usr/bin/env python3
"""Convenience CLI for the single-codebase LaT project."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "models.json"
ALIASES = {"MOE-LIGHT": "MOE_LIGHT", "MOELIGHT": "MOE_LIGHT"}
REQUIRED_PACKAGES = ("torch", "numpy", "scipy", "matplotlib", "tqdm", "pytz")


def load_models():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_model(value):
    key = value.strip().upper()
    return ALIASES.get(key, key)


def select_model(models, value):
    key = normalize_model(value)
    if key not in models:
        raise SystemExit("Unknown model '{}'. Choose: {}".format(value, ", ".join(models)))
    return key


def print_models(models, as_json=False):
    if as_json:
        print(json.dumps(models, indent=2, ensure_ascii=False))
        return 0
    rows = [("MODEL", "CLASS", "TRAINER", "BACKBONE")]
    for key, spec in models.items():
        rows.append((key, spec["class"], spec["trainer_strategy"], spec["backbone"]))
    widths = [max(len(str(row[index])) for row in rows) for index in range(4)]
    for number, row in enumerate(rows):
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
        if number == 0:
            print("  ".join("-" * width for width in widths))
    return 0


def is_lfs_pointer(path):
    try:
        with path.open("rb") as handle:
            return handle.read(80).startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def doctor(models):
    failures = []
    print("Python: {} ({})".format(sys.version.split()[0], sys.executable))
    if sys.version_info < (3, 8):
        failures.append("Python >= 3.8 is required")
    for package in REQUIRED_PACKAGES:
        available = importlib.util.find_spec(package) is not None
        print("  {:7} dependency {}".format("OK" if available else "MISSING", package))
        if not available:
            failures.append("missing dependency: {}".format(package))

    required_paths = (
        ROOT / "train.py", ROOT / "test.py", ROOT / "Trainer.py", ROOT / "Tester.py",
        ROOT / "models", ROOT / "envs", ROOT / "trainers", ROOT / "testers",
    )
    for path in required_paths:
        available = path.exists()
        print("  {:7} {}".format("OK" if available else "MISSING", path.relative_to(ROOT)))
        if not available:
            failures.append("missing unified path: {}".format(path.relative_to(ROOT)))

    try:
        from Trainer import TRAINER_REGISTRY
        from Tester import TESTER_REGISTRY
        from models import CADAModel, MOEModel, MOEModel_Light, MTLModel, ReLDModel
        registered = set(TRAINER_REGISTRY) == set(models) == set(TESTER_REGISTRY)
        classes = (MTLModel, MOEModel, MOEModel_Light, CADAModel, ReLDModel)
        print("  {:7} five model classes imported in one process".format("OK" if len(classes) == 5 else "FAILED"))
        print("  {:7} trainer/tester registries".format("OK" if registered else "FAILED"))
        if not registered:
            failures.append("model/trainer/tester registry mismatch")
    except Exception as exception:
        failures.append("unified import failed: {}".format(exception))
        print("  FAILED  unified imports: {}".format(exception))

    data_files = sorted((ROOT / "data").glob("**/*.pkl"))
    hydrated = [path for path in data_files if not is_lfs_pointer(path)]
    print("  {:7} shared data hydrated: {}/{}".format("OK" if len(hydrated) == len(data_files) and data_files else "FAILED", len(hydrated), len(data_files)))
    if not data_files or len(hydrated) != len(data_files):
        failures.append("shared data is missing or not hydrated; run git lfs pull")

    if failures:
        print("Doctor found problems:")
        for failure in failures:
            print("  - {}".format(failure))
        return 1
    print("Doctor: the unified LaT project is ready.")
    return 0


def build_parser(models):
    parser = argparse.ArgumentParser(description="Run every LaT model from one codebase")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="show unified model registry")
    list_parser.add_argument("--json", action="store_true")
    for command in ("train", "test"):
        child = subparsers.add_parser(command, help="run the unified {} entry".format(command))
        child.add_argument("model", help="one of: {}".format(", ".join(models)))
    subparsers.add_parser("doctor", help="check the single-codebase layout")
    subparsers.add_parser("generate-data", help="run the shared data generator")
    return parser


def main(argv=None):
    models = load_models()
    parser = build_parser(models)
    args, remaining = parser.parse_known_args(argv)
    if args.command == "list":
        if remaining:
            parser.error("unrecognized arguments: {}".format(" ".join(remaining)))
        return print_models(models, args.json)
    if args.command == "doctor":
        if remaining:
            parser.error("unrecognized arguments: {}".format(" ".join(remaining)))
        return doctor(models)
    if args.command == "train":
        model_type = select_model(models, args.model)
        from train import main as train_main
        return train_main(["--model_type", model_type] + remaining)
    if args.command == "test":
        model_type = select_model(models, args.model)
        from test import main as test_main
        return test_main(["--model_type", model_type] + remaining)
    if args.command == "generate-data":
        from generate_data import main as data_main
        return data_main(remaining)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
