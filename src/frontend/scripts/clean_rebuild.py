"""Rebuild an allowlisted source snapshot in a new directory outside the source project.

Existing reports, generated data, environments and build outputs are never copied.
No experiment runner is invoked. This script records its own evidence in the source
project's artifacts directory; a staged copy or stale source snapshot is not a PASS.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from package_delivery import collect_files, EXPECTED_INPUT_SHA256, REQUIRED_FILES

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_files(root: Path) -> list[Path]:
    return [path for path in collect_files(root) if path.relative_to(root).parts[0] != "artifacts"]


def describe_sources(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): {"bytes": path.stat().st_size,
            "sha256": digest(path.read_bytes())} for path in source_files(root)}


def validate_sources(root: Path) -> list[Path]:
    files = source_files(root)
    names = {path.relative_to(root).as_posix() for path in files}
    missing = REQUIRED_FILES - names
    if missing:
        raise ValueError("Source is not ready for full rebuild; missing: " + ", ".join(sorted(missing)))
    archives = [path for path in files if path.relative_to(root).parts[0] == "inputs"]
    if len(archives) != 1 or digest(archives[0].read_bytes()) != EXPECTED_INPUT_SHA256:
        raise ValueError("The single immutable original input ZIP is required")
    return files


def command_plan() -> list[dict]:
    return [
        {"name": "setup", "command": ["bash", "scripts/console.sh", "setup"]},
        {"name": "data-convert", "command": ["bash", "scripts/console.sh", "data-convert"]},
        {"name": "validate", "command": [".venv/bin/python", "scripts/validate_data.py"]},
        {"name": "refresh-validation", "command": [".venv/bin/python", "scripts/convert_data.py", "--refresh-validation"]},
        {"name": "test", "command": ["bash", "scripts/console.sh", "test"]},
        {"name": "build", "command": ["bash", "scripts/console.sh", "build"]},
    ]


def version(command: list[str]) -> dict:
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, timeout=20)
        return {"command": command, "exit_code": result.returncode, "output": result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "error": str(error)}


def save_report(report: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def rebuild(root: Path, parent: Path, report_path: Path, step_timeout: int, stage_only: bool = False) -> dict:
    root = root.resolve(strict=True)
    parent = parent.resolve(strict=True)
    if not parent.is_dir() or parent == root or root in parent.parents:
        raise ValueError("Temporary parent must be an existing directory outside the source project")
    files = validate_sources(root)
    started = time.monotonic()
    destination = Path(tempfile.mkdtemp(prefix="bpp-clean-rebuild-", dir=parent))
    run_id = destination.name
    logs = report_path.parent / "clean_rebuild_logs" / run_id
    logs.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "status": "RUNNING", "started_utc": utc_now(),
              "source_root": str(root), "clean_root": str(destination),
              "scope": "Fresh dependency install, immutable ZIP import, data conversion, full scientific validation, tests and production build",
              "environment": {"platform": platform.platform(),
                              "execution": "WSL" if "microsoft" in platform.release().lower() else platform.system(),
                              "python": version([sys.executable, "--version"]),
                              "node": version(["node", "--version"]), "npm": version(["npm", "--version"])},
              "copied_existing_reports": False, "copied_generated_data": False,
              "copied_dependency_directories": False, "source_files": {}, "steps": [],
              "browser_acceptance_included": False, "real_phone_tested": False}
    save_report(report, report_path)
    try:
        for source in files:
            relative = source.relative_to(root)
            content = source.read_bytes()
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            shutil.copymode(source, target)
            if target.read_bytes() != content:
                raise ValueError(f"Copied source differs: {relative}")
            report["source_files"][relative.as_posix()] = {"bytes": len(content), "sha256": digest(content)}
        forbidden = ("artifacts", "research", "public/data", ".venv", "node_modules", "dist")
        if any((destination / name).exists() for name in forbidden):
            raise ValueError("Staged directory unexpectedly contains generated data, evidence or dependencies")
        report["source_snapshot_sha256"] = digest(json.dumps(report["source_files"], sort_keys=True).encode("utf-8"))
        save_report(report, report_path)
        if stage_only:
            report["status"] = "STAGED_NOT_EXECUTED"
        else:
            environment = os.environ.copy()
            environment["CI"] = "1"
            environment["PYTHONUNBUFFERED"] = "1"
            environment.pop("PYTHONPATH", None)
            environment.pop("PYTHONHOME", None)
            environment.pop("VIRTUAL_ENV", None)
            for index, planned in enumerate(command_plan(), start=1):
                log = logs / f"{index:02d}-{planned['name']}.log"
                step = {**planned, "started_utc": utc_now(), "log": str(log), "status": "RUNNING"}
                report["steps"].append(step)
                save_report(report, report_path)
                print(f"[{index}/6] {planned['name']} — {log}", flush=True)
                step_started = time.monotonic()
                with log.open("w", encoding="utf-8") as output:
                    try:
                        result = subprocess.run(planned["command"], cwd=destination, env=environment,
                                                stdout=output, stderr=subprocess.STDOUT, check=False,
                                                timeout=step_timeout)
                        step["exit_code"] = result.returncode
                        step["status"] = "PASS" if result.returncode == 0 else "FAIL"
                    except subprocess.TimeoutExpired:
                        step.update(status="FAIL", exit_code=None, error=f"Step exceeded {step_timeout} seconds")
                    except OSError as error:
                        step.update(status="FAIL", exit_code=None, error=f"{type(error).__name__}: {error}")
                step["duration_seconds"] = round(time.monotonic() - step_started, 3)
                step["finished_utc"] = utc_now()
                save_report(report, report_path)
                if step["status"] != "PASS":
                    raise RuntimeError(f"Step {planned['name']} failed; see {log}")
            checks = {
                "scientific_validation_pass": json.loads((destination / "artifacts/validation_report.json").read_text(encoding="utf-8")).get("status") == "PASS",
                "exported_validation_pass": json.loads((destination / "public/data/validation.json").read_text(encoding="utf-8")).get("status") == "PASS",
                "production_index_exists": (destination / "dist/index.html").is_file(),
            }
            report["postconditions"] = checks
            if not all(checks.values()):
                raise ValueError("Post-build checks failed: " + ", ".join(key for key, passed in checks.items() if not passed))
            report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        try:
            current = describe_sources(root)
            changed = sorted(name for name in set(current) | set(report["source_files"])
                             if current.get(name) != report["source_files"].get(name))
            report["source_changed_during_run"] = changed
            if changed and report["status"] == "PASS":
                report["status"] = "STALE"
                report["error"] = "Snapshot passed, but source changed during execution; current source is not certified"
        except Exception as error:
            report["source_comparison_error"] = str(error)
            if report["status"] == "PASS":
                report["status"] = "STALE"
        report["finished_utc"] = utc_now()
        report["duration_seconds"] = round(time.monotonic() - started, 3)
        save_report(report, report_path)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--parent", type=Path, default=Path(tempfile.gettempdir()), help="Existing temporary parent outside source; default system /tmp")
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/clean_rebuild.json")
    parser.add_argument("--step-timeout", type=int, default=1800)
    parser.add_argument("--plan", action="store_true", help="Print commands; do not copy, install or execute")
    parser.add_argument("--stage-only", action="store_true", help="Copy source only; record STAGED_NOT_EXECUTED, never PASS")
    args = parser.parse_args()
    if args.step_timeout <= 0:
        parser.error("--step-timeout must be positive")
    if args.plan:
        print(json.dumps(command_plan(), ensure_ascii=False, indent=2))
    else:
        try:
            result = rebuild(args.source, args.parent, args.report.resolve(), args.step_timeout, args.stage_only)
        except (OSError, ValueError) as error:
            parser.exit(1, f"Clean rebuild preflight failed: {error}\n")
        print(json.dumps({key: result[key] for key in ("status", "clean_root", "duration_seconds")}, ensure_ascii=False))
        raise SystemExit(0 if result["status"] in {"PASS", "STAGED_NOT_EXECUTED"} else 1)
