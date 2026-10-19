#!/usr/bin/env python3
"""Rescore 李月莹's 2026-10-16 baseline zip with this repo's checker.

The zip is the raw archive. This script does not change solver code. It writes
independent_verification.json and the two archive packages whose comparison
keys keep the 5s end-to-end scope and the 1s search-loop scope apart.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src/research/src"))

from urp_research.cvrplib.audit import independent_input, validator  # noqa: E402
from urp_research.cvrplib.evaluate import evaluate_saved  # noqa: E402
from urp_research.cvrplib.io import contract_for, digest, parse_sol, parse_vrp  # noqa: E402

COMMIT = "50b3b2c2cc7377e1f13dcaeebce09abf5619dbf8"
EXPECTED_SHA = "a45238ff7430302002dcd68ea5eaa9d006b71a542a897a99f1201a41ae258876"
EXPECTED_BYTES = 12386339
EXPECTED_ENTRIES = 2519
ZIP_REL = "experiments/results/路线求解/李月莹_基线补做_20261016.zip"
OWNER_ZIP = ROOT / "experiments/results/路线求解/公共路线强基线.zip"
MANIFEST = ROOT / "src/research/configs/cvrplib_cases.json"
HANDOFF = Path(__file__).resolve().parent
NOTE_TWO_DECIMALS = {"savings": 24.28, "T": 23.53, "TRS": 13.39, "TSR": 11.85, "pyvrp": 0.31}
SOURCE_PREFIX = "src/research/src/urp_research/cvrplib/"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"])


def load_json_bytes(data: bytes):
    return json.loads(data.decode("utf-8"))


def member(z: zipfile.ZipFile, name: str) -> bytes:
    return z.read(name)


def stdout_payload(blob: bytes) -> dict:
    for line in blob.splitlines():
        if line.startswith(b"{") and b'"routes"' in line:
            payload = json.loads(line)
            payload.pop("stats", None)
            payload.pop("stats_runtime_per_iteration", None)
            payload.pop("native_routes", None)
            return payload
    raise ValueError("stdout has no route JSON")


def case_equal(gaps_by_case: dict[str, list[float]]) -> tuple[float, float, int]:
    case_means = [statistics.mean(values) for values in gaps_by_case.values()]
    return statistics.mean(case_means), statistics.median(case_means), len(case_means)


def check(report: dict, name: str, ok: bool, **detail) -> None:
    row = {"name": name, "pass": bool(ok), **detail}
    report["checks"].append(row)
    print(f"{'PASS' if ok else 'FAIL'} {name}", flush=True)


def extract_summaries(z: zipfile.ZipFile) -> None:
    mapping = {
        "交接说明.md": HANDOFF / "交接说明.md",
        "53例/summary/overview.csv": HANDOFF / "summary/overview.csv",
        "53例/summary/by_size.csv": HANDOFF / "summary/by_size.csv",
        "53例/summary/case_algorithm.csv": HANDOFF / "summary/case_algorithm.csv",
        "53例/summary/protocol.json": HANDOFF / "summary/protocol.json",
        "53例/summary/protocol_pre_run.json": HANDOFF / "summary/protocol_pre_run.json",
        "53例/summary/verification.json": HANDOFF / "summary/verification.json",
        "16例/汇总.json": HANDOFF / "16/汇总.json",
        "16例/逐次拼接_96行.csv": HANDOFF / "16/逐次拼接_96行.csv",
        "16例/逐例拼接_16行.csv": HANDOFF / "16/逐例拼接_16行.csv",
    }
    for src, dst in mapping.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(member(z, src))


def score_53(z: zipfile.ZipFile, manifest: dict) -> dict:
    names = [n for n in z.namelist() if n.startswith("53例/raw/") and n.endswith("/result.json")]
    rows = []
    errors = []
    families = set()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.json"
        for index, name in enumerate(sorted(names), start=1):
            blob = member(z, name)
            out.write_bytes(blob)
            result = json.loads(blob)
            try:
                scored = evaluate_saved(ROOT, MANIFEST, out)
            except Exception as exc:  # checker raises ValueError; keep the first failures
                errors.append({"path": name, "error": str(exc)})
                if len(errors) >= 8:
                    break
                continue
            eligible = bool(scored["eligible_for_gap"])
            if (result.get("purpose") != "acceptance_only" or float(result.get("budget_seconds")) != 5.0
                    or result.get("solver_source_sha256") != "32b7deaacb6f6bef2b7943214217aa47e557b804e36a5ab6be3b93f9bc53b09f"
                    or not eligible or scored["candidate_check"]["reported_cost_checked"] is not True):
                errors.append({"path": name, "purpose": result.get("purpose"), "budget": result.get("budget_seconds"),
                               "eligible": eligible, "status": result.get("status")})
                if len(errors) >= 8:
                    break
                continue
            families.add(result["case_id"].split("-", 1)[0])
            rows.append({
                "case_id": result["case_id"],
                "algorithm": result["algorithm"],
                "seed": int(result["seed"]),
                "cost": int(result["cost"]),
                "status": result["status"],
                "gap_percent": scored["gap_percent"],
                "finished_utc": result.get("finished_utc"),
            })
            if index % 200 == 0:
                print(f"  scored {index}/{len(names)}", flush=True)
    by_alg = defaultdict(lambda: defaultdict(list))
    seeds = defaultdict(set)
    for row in rows:
        by_alg[row["algorithm"]][row["case_id"]].append(row["gap_percent"])
        seeds[row["algorithm"]].add(row["seed"])
    summary = {}
    for algorithm, cases in by_alg.items():
        mean, median, n_cases = case_equal(cases)
        summary[algorithm] = {
            "mean_case_reference_gap_percent": mean,
            "median_case_reference_gap_percent": median,
            "cases": n_cases,
            "calls": sum(len(v) for v in cases.values()),
        }
    return {"rows": rows, "errors": errors, "families": sorted(families), "seeds": {k: sorted(v) for k, v in seeds.items()},
            "summary": summary, "result_files": len(names)}


def score_16(z: zipfile.ZipFile, manifest: dict, owner: zipfile.ZipFile) -> dict:
    batches = {
        "group_r1_20261009": "16例/group_r1_20261009/raw/",
        "bridge_20261016": "16例/bridge_20261016/raw/",
    }
    owner_stdout = {Path(n).name: sha_bytes(owner.read(n))
                    for n in owner.namelist() if n.startswith("public_route_strong_baseline_20261009_r1/raw/calls/") and n.endswith(".stdout")}
    problems = {}
    records = []
    stdout_same = 0
    stdout_compared = 0
    for batch, prefix in batches.items():
        calls = [json.loads(line) for line in member(z, prefix + "results.jsonl").decode().splitlines() if line.strip()]
        for call in calls:
            instance_id = call["instance_id"]
            if instance_id not in problems:
                case = next(c for c in manifest["cases"] if c["case_id"] == instance_id)
                vrp_bytes = (ROOT / case["instance_path"]).read_bytes()
                her_vrp = member(z, f"16例/group_r1_20261009/input/{instance_id}.vrp")
                owner_vrp = owner.read(f"public_route_strong_baseline_20261009_r1/input/{instance_id}.vrp")
                problem = parse_vrp(vrp_bytes.decode())
                contract = contract_for(case, problem, False)
                sol_routes, sol_cost = parse_sol((ROOT / case["reference"]["path"]).read_text())
                parsed = independent_input.parse_vrp(vrp_bytes.decode(), contract["K"])
                reference = validator.validate_solution(parsed, sol_routes, sol_cost)
                her_input = load_json_bytes(member(z, f"16例/group_r1_20261009/input/{instance_id}.json"))
                her_ref = load_json_bytes(member(z, f"16例/group_r1_20261009/references/{instance_id}.json"))
                problems[instance_id] = {
                    "parsed": parsed,
                    "reference_valid": reference["valid"] and reference["reported_cost_checked"],
                    "reference_cost": sol_cost,
                    "input_match": (her_input["coordinates"] == problem["coordinates"]
                                    and her_input["demands"] == problem["demands"]
                                    and her_input["capacity"] == problem["capacity"]
                                    and her_input["K"] == contract["K"]
                                    and her_ref["reference_integer_cost"] == sol_cost),
                    "vrp_match": sha_bytes(vrp_bytes) == sha_bytes(her_vrp) == sha_bytes(owner_vrp),
                }
            blob = member(z, prefix + call["stdout"].removeprefix("raw/"))
            payload = stdout_payload(blob)
            info = problems[instance_id]
            candidate = validator.validate_solution(info["parsed"], payload.get("routes"), payload.get("reported_cost"))
            eligible = bool(info["reference_valid"] and candidate["valid"] and candidate["reported_cost_checked"]
                            and payload.get("version") == "0.14.0" and payload.get("algorithm") == "ILS"
                            and float(payload.get("max_runtime_seconds")) == 1.0 and int(payload.get("seed")) == int(call["seed"]))
            gap = float(Fraction(100 * (candidate["cost"] - info["reference_cost"]), info["reference_cost"])) if eligible else None
            if batch == "group_r1_20261009":
                stdout_compared += 1
                stdout_same += int(sha_bytes(blob) == owner_stdout.get(Path(call["stdout"]).name))
            records.append({
                "batch": batch,
                "instance_id": instance_id,
                "seed": int(call["seed"]),
                "cost": payload.get("reported_cost"),
                "gap_percent": gap,
                "eligible": eligible,
                "num_iterations": payload.get("num_iterations"),
                "solver_loop_runtime": payload.get("solver_loop_runtime"),
                "payload_sha256": call.get("payload_sha256"),
                "errors": candidate["errors"][:4],
            })
    return {"records": records, "problems": {k: {"input_match": v["input_match"], "vrp_match": v["vrp_match"],
                                                 "reference_cost": v["reference_cost"]} for k, v in problems.items()},
            "stdout_same": stdout_same, "stdout_compared": stdout_compared, "owner_stdout": len(owner_stdout)}


def formal_overlap(rows: list[dict]) -> dict:
    formal = {}
    with (ROOT / "experiments/baselines/cvrp/results/runs.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            formal[(row["case_id"], row["algorithm"], int(row["seed"]))] = row
    same = diff = absent = 0
    by_alg = defaultdict(lambda: {"same": 0, "different": 0, "absent": 0})
    differences = []
    for row in rows:
        key = (row["case_id"], row["algorithm"], row["seed"])
        other = formal.get(key)
        if other is None:
            absent += 1
            by_alg[row["algorithm"]]["absent"] += 1
            continue
        if int(float(other["cost"])) == row["cost"]:
            same += 1
            by_alg[row["algorithm"]]["same"] += 1
        else:
            diff += 1
            by_alg[row["algorithm"]]["different"] += 1
            differences.append({
                "case_id": row["case_id"], "algorithm": row["algorithm"], "seed": row["seed"],
                "hers": row["cost"], "formal": int(float(other["cost"])),
                "her_status": row["status"], "formal_status": other["status"],
                "formal_host_id": other["host_id"], "formal_resource_cohort": other["resource_cohort"],
            })
    return {"same_cost": same, "different_cost": diff, "absent_from_formal_plan": absent,
            "by_algorithm": by_alg, "differences": differences}


def source_check(pre: dict) -> dict:
    listed = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", COMMIT, SOURCE_PREFIX], text=True)
    py_files = [line for line in listed.splitlines() if line.endswith(".py")]
    hashes = {}
    mismatches = []
    for path in py_files:
        relative = path[len(SOURCE_PREFIX):]
        digest_hex = sha_bytes(git_bytes(COMMIT, path))
        hashes[relative] = digest_hex
        if pre["source_file_sha256"].get(relative) != digest_hex:
            mismatches.append(relative)
    extra = sorted(set(pre["source_file_sha256"]) - set(hashes))
    solver = digest(hashes)
    manifest_commit = sha_bytes(git_bytes(COMMIT, "src/research/configs/cvrplib_cases.json"))
    manifest_head = sha_bytes(MANIFEST.read_bytes())
    formal = subprocess.run(["git", "cat-file", "-e", f"{COMMIT}:protocol/formal_plan.json"], check=False, stderr=subprocess.DEVNULL)
    return {
        "py_files": len(py_files),
        "mismatches": mismatches,
        "extra_in_her_freeze": extra,
        "solver_commit": solver,
        "solver_hers": pre["solver_source_sha256"],
        "manifest_commit": manifest_commit,
        "manifest_hers": pre["manifest_sha256"],
        "manifest_head": manifest_head,
        "repository_source_modified": pre["repository_source_modified"],
        "formal_plan_present_at_commit": formal.returncode == 0,
    }


def write_packages(report: dict, pre: dict) -> None:
    alg = report["summary_53"]
    batches = report["summary_16"]["batches"]
    provenance = {
        "who": "李月莹",
        "handoff_note": "交接说明.md",
        "recorded_unix_home": pre["execution_root"],
        "results_root": pre["results_root"],
        "home_directory_is_a_path_in_the_freeze_not_a_second_author_name": True,
        "frozen_utc": pre["frozen_utc"],
        "bridge_started_utc": report["bridge_started_utc"],
        "bridge_finished_utc": report["bridge_finished_utc"],
        "r1_finished_utc": report["r1_finished_utc"],
        "repo_commit": COMMIT,
        "repository_source_modified": False,
        "pyvrp": pre["pyvrp"],
        "python": pre["python"],
        "package_sha256": EXPECTED_SHA,
        "package_bytes": EXPECTED_BYTES,
        "package_entries": EXPECTED_ENTRIES,
        "zip_relative_path": ZIP_REL,
        "purpose": "acceptance_only",
        "g5_formal_batch": False,
    }
    (HANDOFF / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    scores_53 = {"algorithms": alg, "valid_calls": report["valid_53"], "scheduled_calls": 742,
                 "timing_scope": "5s_end_to_end", "source": "independent rescore with urp_research.cvrplib.evaluate.evaluate_saved"}
    headline_53 = (
        "53 例等权平均 reference gap：savings {savings:.2f}%，T {T:.2f}%，TRS {TRS:.2f}%，TSR {TSR:.2f}%，PyVRP {pyvrp:.2f}%"
        "（742/742 有效；5 秒端到端，含启动/导入/建模/搜索）"
    ).format(**{name: alg[name]["mean_case_reference_gap_percent"] for name in ("savings", "T", "TRS", "TSR", "pyvrp")})
    contract_53 = {
        "metric": "mean_case_reference_gap_percent",
        "unit": "%",
        "direction": "min",
        "cohort": "cvrplib_53_A_B_E_F_P_X_equal_case",
        "protocol": "acceptance_only_commit_50b3b2c_not_G5_formal",
        "budget": "5s_end_to_end_wall_including_startup_import_modelling_search",
        "aggregation": "unweighted_mean_of_53_case_means",
        "reference": "repo_cvrplib_cases_json_verified_sol_not_proved_optimal",
    }
    median_contract = {**contract_53, "metric": "median_case_reference_gap_percent", "aggregation": "median_of_53_case_means"}
    metrics_53 = []
    for name in ("savings", "T", "TRS", "TSR", "pyvrp"):
        metrics_53.append({
            "id": f"{name}-mean-gap", "label": f"{name} 53 例等权平均 reference gap", "algorithm": name,
            "value": alg[name]["mean_case_reference_gap_percent"], "comparison": contract_53,
            "source": {"artifact_id": "independent-scores", "locator": f"/algorithms/{name}/mean_case_reference_gap_percent"},
        })
        metrics_53.append({
            "id": f"{name}-median-gap", "label": f"{name} 53 例 case-mean 中位 reference gap", "algorithm": name,
            "value": alg[name]["median_case_reference_gap_percent"], "comparison": median_contract,
            "source": {"artifact_id": "independent-scores", "locator": f"/algorithms/{name}/median_case_reference_gap_percent"},
        })
    package_53 = {
        "schema_version": 1,
        "id": "cvrplib-53-e2e-5s-20261016",
        "title": "CVRPLIB 53 例统一基线（5 秒端到端，验收补做）",
        "domain": "CVRP",
        "kind": "cvrplib_acceptance_baseline",
        "status": "completed",
        "started_at": pre["frozen_utc"],
        "finished_at": report["finished_53_max"],
        "counts": [
            {"unit": "call", "value": 742, "scope": "acceptance_only_5s_end_to_end", "note": "savings/T/TRS/TSR seed 0 plus PyVRP seeds 0-9"},
            {"unit": "valid_call", "value": report["valid_53"], "scope": "independent_rescore", "note": "repo evaluate_saved plus purpose/budget/source checks"},
            {"unit": "case", "value": 53, "scope": "A_B_E_F_P_X", "note": "equal-case mean; duplicate bases stay in the 53-case denominator"},
        ],
        "failure_reason": None,
        "failures": [],
        "notes": [
            headline_53,
            "计时是 Linux 监督器墙钟，从请求序列化/进程启动前到收到检查点，包含启动、导入、建模和搜索。不能与 1 秒搜索循环 MaxRuntime 合成同一预算。",
            "全部 742 条 purpose=acceptance_only。提交 50b3b2c 上还没有 protocol/formal_plan.json。这不是 G5 正式批次。",
            "交接说明署名为李月莹。冻结记录里的执行目录是 /home/blair/urp_baseline_v2，该路径只说明机器账户，不另立作者。",
            "原始压缩包只保存一份：experiments/results/路线求解/李月莹_基线补做_20261016.zip。",
        ],
        "parameters": {
            "timing_scope": "5s_end_to_end",
            "headline": headline_53,
            "do_not_merge_with": "cvrplib-16-searchloop-1s-20261016",
            "repo_commit": COMMIT,
            "pyvrp": "0.14.0",
            "algorithms": ["savings", "T", "TRS", "TSR", "pyvrp"],
            "constructive_seed": 0,
            "pyvrp_seeds": list(range(10)),
            "g5_formal_batch": False,
        },
        "provenance": provenance,
        "artifacts": [
            {"id": "independent-scores", "path": "independent_scores.json", "media_type": "application/json"},
            {"id": "overview-csv", "path": "overview.csv", "media_type": "text/csv"},
            {"id": "by-size-csv", "path": "by_size.csv", "media_type": "text/csv"},
            {"id": "her-verification", "path": "her_verification.json", "media_type": "application/json"},
            {"id": "provenance", "path": "provenance.json", "media_type": "application/json"},
        ],
        "metrics": metrics_53,
    }
    old = batches["group_r1_20261009"]
    new = batches["bridge_20261016"]
    headline_16 = (
        f"同协议两批并列（不是 6 个独立种子）：原 r1 批平均 gap {old['mean_reference_gap_percent']:.6f}%，"
        f"新批 {new['mean_reference_gap_percent']:.6f}%；{report['summary_16']['identical_costs']}/48 同成本。"
        "计时是搜索循环 MaxRuntime(1.0)，不含启动。"
    )
    def batch_contract(cohort: str) -> dict:
        return {
            "metric": "mean_reference_gap_percent",
            "unit": "%",
            "direction": "min",
            "cohort": cohort,
            "protocol": "archived_r1_inputs_pyvrp_0.14.0_default_ILS_seeds_0_1_2_fresh_process",
            "budget": "1s_search_loop_MaxRuntime_excludes_startup_import_model",
            "aggregation": "mean_of_per_instance_mean_of_seeds_0_1_2",
            "reference": "repo_cvrplib_cases_json_verified_sol_not_proved_optimal",
        }
    historical = {
        "metric": "mean_reference_gap_percent",
        "unit": "%",
        "direction": "min",
        "cohort": "historical_tsr_16_quality_reference",
        "protocol": "historical_TSR_different_algorithm_and_budget_quality_reference_only",
        "budget": "not_the_1s_pyvrp_search_loop",
        "aggregation": "mean_of_per_instance_historical_tsr_gap",
        "reference": "repo_cvrplib_cases_json_verified_sol_not_proved_optimal",
    }
    package_16 = {
        "schema_version": 1,
        "id": "cvrplib-16-searchloop-1s-20261016",
        "title": "CVRPLIB 16 例同协议两批（1 秒搜索循环）",
        "domain": "CVRP",
        "kind": "cvrplib_search_loop_bridge",
        "status": "completed",
        "started_at": report["bridge_started_utc"],
        "finished_at": report["bridge_finished_utc"],
        "counts": [
            {"unit": "call", "value": 48, "scope": "batch_group_r1_20261009", "note": "owner r1 raw stdout, byte-identical in this handoff"},
            {"unit": "call", "value": 48, "scope": "batch_bridge_20261016", "note": "fresh-process bridge; same inputs, seeds and MaxRuntime"},
            {"unit": "identical_cost_pair", "value": report["summary_16"]["identical_costs"], "scope": "same_instance_same_seed", "note": "7 costs differ; new batch is not a sixth seed"},
        ],
        "failure_reason": None,
        "failures": [],
        "notes": [
            headline_16,
            "两批使用相同的 seed 0/1/2，按批次并列。比较键的 cohort 不同，接口不会把它们并成 6 个独立种子。",
            "1 秒是 PyVRP ILS 的 MaxRuntime，从搜索循环内的停止回调计时，不含启动、导入和建模。不能与 5 秒端到端墙钟合成。",
            "历史 TSR 使用另一套算法和预算，只作解质量参照，比较键与这两批不同。",
            "7 个成本差都出在墙钟停止之后：同一 payload 哈希、同一 PyVRP 0.14.0、搜索循环都约 1.000 秒，新批迭代更多。协议已写明墙钟停止不保证逐位相同。",
        ],
        "parameters": {
            "timing_scope": "1s_search_loop",
            "headline": headline_16,
            "do_not_merge_with": "cvrplib-53-e2e-5s-20261016",
            "batches_are_not_six_independent_seeds": True,
            "repo_commit_of_bridge_driver_inputs": COMMIT,
            "pyvrp": "0.14.0",
            "seeds": [0, 1, 2],
            "g5_formal_batch": False,
        },
        "provenance": provenance,
        "artifacts": [
            {"id": "independent-scores", "path": "independent_scores.json", "media_type": "application/json"},
            {"id": "her-summary", "path": "汇总.json", "media_type": "application/json"},
            {"id": "per-instance", "path": "逐例拼接_16行.csv", "media_type": "text/csv"},
            {"id": "per-call", "path": "逐次拼接_96行.csv", "media_type": "text/csv"},
            {"id": "provenance", "path": "provenance.json", "media_type": "application/json"},
        ],
        "metrics": [
            {"id": "batch-r1-mean-gap", "label": "原 r1 批 16 例等权平均 reference gap", "algorithm": "pyvrp",
             "value": old["mean_reference_gap_percent"], "comparison": batch_contract("batch_group_r1_20261009"),
             "source": {"artifact_id": "independent-scores", "locator": "/batches/group_r1_20261009/mean_reference_gap_percent"}},
            {"id": "batch-r1-median-gap", "label": "原 r1 批实例平均 gap 的中位数", "algorithm": "pyvrp",
             "value": old["median_of_instance_means"], "comparison": {**batch_contract("batch_group_r1_20261009"), "metric": "median_of_instance_mean_reference_gap_percent", "aggregation": "median_of_16_instance_means"},
             "source": {"artifact_id": "independent-scores", "locator": "/batches/group_r1_20261009/median_of_instance_means"}},
            {"id": "batch-bridge-mean-gap", "label": "2026-10-16 新批 16 例等权平均 reference gap", "algorithm": "pyvrp",
             "value": new["mean_reference_gap_percent"], "comparison": batch_contract("batch_bridge_20261016"),
             "source": {"artifact_id": "independent-scores", "locator": "/batches/bridge_20261016/mean_reference_gap_percent"}},
            {"id": "batch-bridge-median-gap", "label": "新批实例平均 gap 的中位数", "algorithm": "pyvrp",
             "value": new["median_of_instance_means"], "comparison": {**batch_contract("batch_bridge_20261016"), "metric": "median_of_instance_mean_reference_gap_percent", "aggregation": "median_of_16_instance_means"},
             "source": {"artifact_id": "independent-scores", "locator": "/batches/bridge_20261016/median_of_instance_means"}},
            {"id": "historical-tsr-mean-gap", "label": "历史 TSR 16 例平均 reference gap（质量参照）", "algorithm": "historical_TSR",
             "value": report["summary_16"]["historical_tsr_mean"], "comparison": historical,
             "source": {"artifact_id": "her-summary", "locator": "/historical_TSR_mean_reference_gap_percent"}},
        ],
    }
    write_package(ROOT / "data/packages/cvrplib-53-e2e-5s-20261016", package_53, {
        "independent_scores.json": json.dumps(scores_53, ensure_ascii=False, indent=2).encode() + b"\n",
        "overview.csv": (HANDOFF / "summary/overview.csv").read_bytes(),
        "by_size.csv": (HANDOFF / "summary/by_size.csv").read_bytes(),
        "her_verification.json": (HANDOFF / "summary/verification.json").read_bytes(),
        "provenance.json": (HANDOFF / "provenance.json").read_bytes(),
    })
    write_package(ROOT / "data/packages/cvrplib-16-searchloop-1s-20261016", package_16, {
        "independent_scores.json": json.dumps(report["summary_16"], ensure_ascii=False, indent=2).encode() + b"\n",
        "汇总.json": (HANDOFF / "16/汇总.json").read_bytes(),
        "逐例拼接_16行.csv": (HANDOFF / "16/逐例拼接_16行.csv").read_bytes(),
        "逐次拼接_96行.csv": (HANDOFF / "16/逐次拼接_96行.csv").read_bytes(),
        "provenance.json": (HANDOFF / "provenance.json").read_bytes(),
    })


def write_package(directory: Path, descriptor: dict, files: dict[str, bytes]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        (directory / name).write_bytes(blob)
    (directory / "experiment.json").write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    os.chdir(ROOT)
    report = {"checks": []}
    zip_path = ROOT / ZIP_REL
    blob = zip_path.read_bytes()
    digest_hex = sha_bytes(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        flags = {bool(info.flag_bits & 0x800) for info in z.infolist()}
        check(report, "zip_sha256", digest_hex == EXPECTED_SHA and len(blob) == EXPECTED_BYTES and len(z.infolist()) == EXPECTED_ENTRIES and flags == {True},
              sha256=digest_hex, bytes=len(blob), entries=len(z.infolist()), utf8_flag=True,
              note="UTF-8 flag is set on every member; names are already Unicode. cp437 reinterpretation would corrupt them.")
        checksum = json.loads((HANDOFF / "校验信息.json").read_text(encoding="utf-8"))
        check(report, "checksum_file", checksum["sha256"] == EXPECTED_SHA and checksum["bytes"] == EXPECTED_BYTES and checksum["entries"] == EXPECTED_ENTRIES
              and checksum["effective_53_calls"] == 742 and checksum["effective_16_old_calls"] == 48 and checksum["effective_16_new_calls"] == 48,
              package=checksum.get("package"))
        extract_summaries(z)
        pre = load_json_bytes(member(z, "53例/summary/protocol_pre_run.json"))
        source = source_check(pre)
        check(report, "commit_50b3b2c_source_unchanged",
              source["mismatches"] == [] and source["extra_in_her_freeze"] == [] and source["solver_commit"] == source["solver_hers"]
              and source["manifest_commit"] == source["manifest_hers"] == source["manifest_head"]
              and source["repository_source_modified"] is False and source["formal_plan_present_at_commit"] is False,
              **source)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        print("scoring 53-case results", flush=True)
        scored = score_53(z, manifest)
        check(report, "53_rescore_742", scored["result_files"] == 742 and len(scored["rows"]) == 742 and not scored["errors"]
              and scored["families"] == ["A", "B", "E", "F", "P", "X"] and scored["seeds"] == {
                  "savings": [0], "T": [0], "TRS": [0], "TSR": [0], "pyvrp": list(range(10))},
              rows=len(scored["rows"]), bad=len(scored["errors"]), bad_sample=scored["errors"][:3], families=scored["families"])
        overview = {}
        with (HANDOFF / "summary/overview.csv").open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                overview[row["algorithm"]] = row
        mean_ok = True
        detail = {}
        for name, item in scored["summary"].items():
            claimed = float(overview[name]["mean_case_gap_percent_complete_only"])
            claimed_median = float(overview[name]["median_case_gap_percent_complete_only"])
            detail[name] = {"got_mean": item["mean_case_reference_gap_percent"], "claimed_overview_mean": claimed,
                            "mean_abs": abs(item["mean_case_reference_gap_percent"] - claimed),
                            "got_median": item["median_case_reference_gap_percent"], "median_abs": abs(item["median_case_reference_gap_percent"] - claimed_median),
                            "calls": item["calls"], "cases": item["cases"]}
            mean_ok = mean_ok and detail[name]["mean_abs"] < 5e-7 and detail[name]["median_abs"] < 5e-7
            mean_ok = mean_ok and round(item["mean_case_reference_gap_percent"] + 1e-12, 2) == NOTE_TWO_DECIMALS[name]
        check(report, "53_means_medians", mean_ok, detail=detail)
        overlap = formal_overlap(scored["rows"])
        report["formal_overlap"] = {k: overlap[k] for k in ("same_cost", "different_cost", "absent_from_formal_plan", "by_algorithm")}
        report["formal_differences"] = overlap["differences"]
        print(f"INFO 53_vs_formal same={overlap['same_cost']} different={overlap['different_cost']} absent={overlap['absent_from_formal_plan']}", flush=True)
        with zipfile.ZipFile(OWNER_ZIP) as owner:
            sixteen = score_16(z, manifest, owner)
            protocol_same = sha_bytes(member(z, "16例/group_r1_20261009/freeze/PROTOCOL.json")) == sha_bytes(owner.read("public_route_strong_baseline_20261009_r1/freeze/PROTOCOL.json"))
            schedule_same = sha_bytes(member(z, "16例/group_r1_20261009/freeze/SCHEDULE.json")) == sha_bytes(owner.read("public_route_strong_baseline_20261009_r1/freeze/SCHEDULE.json"))
            per_seed_same = sha_bytes(member(z, "16例/group_r1_20261009/reports/PER_SEED.csv")) == sha_bytes(owner.read("public_route_strong_baseline_20261009_r1/reports/PER_SEED.csv"))
            worker_her = member(z, "16例/group_r1_20261009/source/worker.py")
            worker_same = sha_bytes(worker_her) == sha_bytes(owner.read("public_route_strong_baseline_20261009_r1/source/worker.py")) == pre["source_file_sha256"]["frozen/pyvrp/worker.py"]
        check(report, "16_inputs_protocol_match_owner",
              sixteen["stdout_same"] == 48 and sixteen["stdout_compared"] == 48 and protocol_same and schedule_same and per_seed_same and worker_same
              and all(v["input_match"] and v["vrp_match"] for v in sixteen["problems"].values()) and len(sixteen["problems"]) == 16,
              instances=len(sixteen["problems"]), stdout_same=sixteen["stdout_same"], protocol_same=protocol_same,
              schedule_same=schedule_same, per_seed_same=per_seed_same, worker_sha256=sha_bytes(worker_her))
        by_batch = defaultdict(list)
        paired = {}
        bad_16 = []
        for row in sixteen["records"]:
            if not row["eligible"]:
                bad_16.append(row)
            else:
                by_batch[row["batch"]].append(row)
                paired.setdefault((row["instance_id"], row["seed"]), {})[row["batch"]] = row
        def batch_stats(rows: list[dict]) -> dict:
            grouped = defaultdict(list)
            for row in rows:
                grouped[row["instance_id"]].append(row["gap_percent"])
            instance_means = [statistics.mean(v) for v in grouped.values()]
            return {"calls": len(rows), "valid": len(rows), "mean_reference_gap_percent": statistics.mean(instance_means),
                    "median_of_instance_means": statistics.median(instance_means),
                    "median_of_seed_gaps": statistics.median([row["gap_percent"] for row in rows])}
        batch_summary = {name: batch_stats(rows) for name, rows in by_batch.items()}
        identical = 0
        differences = []
        for key, pair in sorted(paired.items()):
            old, new = pair["group_r1_20261009"], pair["bridge_20261016"]
            if old["cost"] == new["cost"]:
                identical += 1
            else:
                differences.append({"instance_id": key[0], "seed": key[1], "old_cost": old["cost"], "new_cost": new["cost"],
                                    "old_gap_percent": old["gap_percent"], "new_gap_percent": new["gap_percent"],
                                    "old_iterations": old["num_iterations"], "new_iterations": new["num_iterations"],
                                    "old_solver_loop_runtime": old["solver_loop_runtime"], "new_solver_loop_runtime": new["solver_loop_runtime"],
                                    "payload_sha256_equal": old["payload_sha256"] == new["payload_sha256"]})
        claimed = load_json_bytes(member(z, "16例/汇总.json"))
        mean_close = (abs(batch_summary["group_r1_20261009"]["mean_reference_gap_percent"] - claimed["group_mean_reference_gap_percent"]) < 1e-12
                      and abs(batch_summary["bridge_20261016"]["mean_reference_gap_percent"] - claimed["bridge_mean_reference_gap_percent"]) < 1e-12)
        check(report, "16_rescore_48_48",
              len(bad_16) == 0 and batch_summary["group_r1_20261009"]["valid"] == 48 and batch_summary["bridge_20261016"]["valid"] == 48
              and identical == 41 and len(differences) == 7 and mean_close
              and claimed["same_cost_seed_pairs"] == 41 and round(batch_summary["group_r1_20261009"]["mean_reference_gap_percent"] + 1e-15, 6) == 0.148747
              and round(batch_summary["bridge_20261016"]["mean_reference_gap_percent"] + 1e-15, 6) == 0.075207,
              batches=batch_summary, identical=identical, differences=differences, bad=len(bad_16))
        report["summary_53"] = scored["summary"]
        report["valid_53"] = len(scored["rows"])
        report["finished_53_max"] = max(row["finished_utc"] for row in scored["rows"] if row.get("finished_utc"))
        report["bridge_started_utc"] = load_json_bytes(member(z, "16例/bridge_20261016/raw/STARTED.json"))["utc"]
        report["bridge_finished_utc"] = load_json_bytes(member(z, "16例/bridge_20261016/raw/FINISHED.json"))["utc"]
        report["r1_finished_utc"] = load_json_bytes(member(z, "16例/group_r1_20261009/raw/FINISHED.json"))["utc"]
        report["summary_16"] = {"batches": batch_summary, "identical_costs": identical, "cost_differences": differences,
                                "historical_tsr_mean": claimed["historical_TSR_mean_reference_gap_percent"]}
        report["registry_files"] = sum(1 for n in z.namelist() if n.startswith("53例/run_registry/") and n.endswith(".json"))
    slim = {k: v for k, v in report.items() if k != "checks"}
    # Drop bulky per-call rows; checks already carry the 7 differences and the formal list.
    out = {"checks": report["checks"], **slim}
    (HANDOFF / "independent_verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if all(item["pass"] for item in report["checks"]):
        write_packages(report, pre)
        print("packages written", flush=True)
        return 0
    print("verification failed; packages not written", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
