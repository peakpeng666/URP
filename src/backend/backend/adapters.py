"""Read-only adapters for the selected, already-executed research snapshots.

Only named public snapshot files are read. No solver, network, or model is invoked.
Artifacts are copied byte-for-byte and checked against the source catalog hashes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def _slug(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value)).strip("-")


def _status(value: Any, failures: Any = None) -> str:
    """Normalize observed execution status; missing status is never 'live'."""
    normalized = str(value or "").strip().lower()
    mapped = {"complete": "completed", "completed": "completed", "pass": "completed",
              "success": "completed", "running": "running", "queued": "queued",
              "pending": "queued", "failed": "failed", "failure": "failed",
              "error": "failed", "partial": "partial", "unknown": "unknown"}.get(normalized)
    if mapped:
        return "partial" if mapped == "completed" and (_number(failures) or 0) > 0 else mapped
    return "failed" if (_number(failures) or 0) > 0 else "unknown"


def _count(unit: str, value: Any, scope: str, note: str) -> dict:
    numeric = _number(value)
    if numeric is not None and numeric.is_integer():
        numeric = int(numeric)
    return {"unit": unit, "value": numeric, "scope": scope, "note": note}


def _comparison(metric: str, unit: str, direction: str, cohort: str,
                protocol: str, budget: str, aggregation: str, reference: str) -> dict:
    return dict(metric=metric, unit=unit, direction=direction, cohort=cohort,
                protocol=protocol, budget=budget, aggregation=aggregation, reference=reference)


def _metric(id_: str, label: str, algorithm: str, value: Any, comparison: dict,
            artifact_id: str, locator: str) -> dict:
    return {"id": id_, "label": label, "algorithm": algorithm, "value": _number(value),
            "comparison": comparison, "source": {"artifact_id": artifact_id, "locator": locator}}


def _artifact_role(name: str) -> str:
    lowered = name.lower()
    if "failure" in lowered or "launch_attempt" in lowered:
        return "failure"
    if "audit" in lowered or "validation" in lowered or "check" in lowered:
        return "audit"
    if lowered.endswith((".md", ".txt")):
        return "report"
    if "summary" in lowered:
        return "summary"
    return "provenance"


def _copy_files(destination: Path, source: Path, entries: list[dict]) -> tuple[list[dict], dict[str, str]]:
    artifacts, mapping = [], {}
    source = source.resolve()
    for entry in entries:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe snapshot path: {relative}")
        original = (source / relative).resolve()
        if not original.is_relative_to(source) or not original.is_file():
            raise ValueError(f"Missing or unsafe snapshot artifact: {relative}")
        data = original.read_bytes()
        if entry.get("sha256") and hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Source snapshot hash mismatch: {relative}")
        if entry.get("bytes") is not None and len(data) != entry["bytes"]:
            raise ValueError(f"Source snapshot length mismatch: {relative}")
        artifact_id = _slug(relative.as_posix())
        if artifact_id in mapping.values():
            raise ValueError(f"Duplicate artifact id: {artifact_id}")
        target = destination / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        if target.read_bytes() != data:
            raise ValueError(f"Artifact copy did not preserve original bytes: {relative}")
        mapping[relative.as_posix()] = artifact_id
        artifacts.append({"id": artifact_id, "path": (Path("files") / relative).as_posix(),
                          "media_type": {".json": "application/json", ".csv": "text/csv",
                                         ".md": "text/markdown", ".txt": "text/plain"}.get(relative.suffix.lower(), "application/octet-stream"),
                          "role": _artifact_role(relative.name)})
    return artifacts, mapping


def _base(id_: str, title: str, domain: str, kind: str, captured: str, label: str) -> dict:
    return {"schema_version": 1, "id": id_, "title": title, "domain": domain, "kind": kind,
            "status": "unknown", "started_at": None, "finished_at": None, "counts": [],
            "failure_reason": None, "failures": None, "notes": [], "parameters": {},
            "provenance": {"captured_at": captured, "source_label": label},
            "metrics": [], "artifacts": []}


def _save(destination: Path, experiment: dict) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "experiment.json"
    path.write_text(json.dumps(experiment, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path


def _selector(source: Path, destination: Path, batch: dict, captured: str) -> Path:
    rows, done, cost, audit = (_read(source / p) for p in ("SUMMARY.json", "RUN_COMPLETE.json", "COST.json", "AUDIT.json"))
    e = _base("selector", batch["title"], "BPP", "offline_training_size_ablation", captured, "public/research-batches/selector")
    e["artifacts"], refs = _copy_files(destination, source, batch["files"])
    e["status"] = _status(cost.get("status"), audit.get("failure_count"))
    e["failures"] = [] if audit.get("failure_count") == 0 else None
    e["finished_at"] = done.get("utc")
    if e["status"] in {"failed", "partial"}:
        e["failure_reason"] = f"Recorded numerical failure count: {audit.get('failure_count', 'unknown')}"
    e["counts"] = [
        _count("fit", done.get("new_offline_fits"), "offline_training", "RUN_COMPLETE.json:new_offline_fits; includes fold fits, not policy executions"),
        _count("decision", done.get("new_offline_test_predictions"), "offline_prediction", "RUN_COMPLETE.json:new_offline_test_predictions; training-subset seeds reuse the fixed test set"),
        _count("run", done.get("new_policy_runs"), "new_policy", "RUN_COMPLETE.json:new_policy_runs; historical policies were not rerun"),
        _count("stream", cost.get("unique_test_streams"), "fixed_test", "COST.json:unique_test_streams; 36 multisets × 3 correlated orders, not 108 independent samples"),
        _count("run", cost.get("historical_raw_label_runs_verified"), "historical_label_subset_verified", "COST.json:historical_raw_label_runs_verified; only source labels checked in this ablation, not the entire 768-run historical project"),
    ]
    e["notes"] = [batch["scope"], batch["note"], batch["failures"],
        "family_holdout 和 within_family 使用不同 cohort，不能混为一条学习曲线。",
        "同一测试口径的训练档位可比较；20 个种子仅改变训练子集，满量级子集相同。",
        "只导入已经完成的离线分析，没有运行新策略；源快照没有起始时间，保留 null。"]
    e["parameters"] = {"model": "fixed 5NN cost regression", "k": 5, "prefix_items": 500,
        "feature_count": 31, "test_multisets": 36, "orders_per_multiset": 3,
        "historical_test_already_observed": True,
        "training_grid": [{k: r[k] for k in ("track", "train_groups", "train_streams", "groups_per_training_family", "seeds", "test_streams_fixed")} for r in rows]}
    fields = [("mean_bins", "平均箱数", "bins", "absolute observed bin count"),
              ("delta_vs_subset_sbs", "选择器减去 SBS", "bins", "training-subset SBS; observed BF_then_EoH on all grid points"),
              ("regret", "两后缀分支 oracle regret", "bins", "hindsight minimum of BF and BF_then_EoH after shared BF prefix; not global optimum")]
    for index, r in enumerate(rows):
        track, groups = r["track"], r["train_groups"]
        algorithm = f"SELECTOR ({groups} groups / {r['train_streams']} streams)"
        for field, label, unit, reference in fields:
            c = _comparison(field, unit, "min", f"selector:{track}:fixed-108-streams:36-multisets",
                f"retrospective fixed-5NN training-size ablation; track={track}; frozen before refit",
                "fixed k=5 and prefix=500; training-group count is the learning-curve axis",
                f"mean of per-stream outcomes across {r['seeds']} training-subset seeds; correlated fixed test set", reference)
            e["metrics"].append(_metric(f"{track}-{groups}-{field}", f"{label} · {track}", algorithm,
                r.get(field, {}).get("mean"), c, refs["SUMMARY.json"], f"/{index}/{field}/mean"))
    return _save(destination, e)


def _budget(source: Path, destination: Path, batch: dict, captured: str) -> Path:
    summary, done, resource, failures, launch = (_read(source / p) for p in (
        "reports/SUMMARY.json", "raw/COMPLETION.json", "reports/RESOURCE_ACCOUNTING.json", "failures/FAILURES.json", "failures/ANALYSIS_LAUNCH_ATTEMPT_1.json"))
    rows = summary["summary"]
    e = _base("budget", batch["title"], "CVRP", "search_budget_ablation", captured, "public/research-batches/budget")
    e["artifacts"], refs = _copy_files(destination, source, batch["files"])
    e["status"] = _status(batch.get("status"), done.get("failure_count"))
    e["failures"] = [{"phase": "analysis_launch", "status": "recovered",
                      "reason": launch.get("error"), "resolution": launch.get("resolution"),
                      "source": {"artifact_id": refs["failures/ANALYSIS_LAUNCH_ATTEMPT_1.json"], "locator": "/error"}}]
    e["started_at"] = resource.get("numerical_task_start_utc")
    e["finished_at"] = done.get("utc")
    if e["status"] in {"failed", "partial"}:
        e["failure_reason"] = f"Recorded formal trajectory failure count: {done.get('failure_count', 'unknown')}"
    budgets = sorted({r["budget"] for r in rows})
    trajectory_count = _number(done.get("rows"))
    e["counts"] = [
        _count("trajectory", trajectory_count, "formal", "raw/COMPLETION.json:rows; each executed once to the maximum budget"),
        _count("checkpoint", trajectory_count * len(budgets) if trajectory_count is not None else None,
            "formal", "COMPLETION rows × 4 frozen budget levels; correlated checkpoints, not independent runs"),
        _count("geometry", len(summary["common_support_geometries"]), "formal_independent_blocks", "reports/SUMMARY.json:common_support_geometries; independent pairing unit"),
        _count("run", 16, "smoke_standalone", "reports/REPORT_ZH.md: 4 algorithms × 4 independently capped reference runs; excluded from formal trajectories"),
        _count("trajectory", 4, "smoke_checkpoint", "reports/REPORT_ZH.md: 4 longest trajectories checked against the 16 standalone references"),
    ]
    e["notes"] = [batch["scope"], batch["note"], batch["failures"],
        "比较键包含 delta 评价预算与需求组，仅同预算、同需求口径的四算法可以直接比较。",
        "等评价不等于等 FLOPs 或等时间；不同检查点相关；不将相对面板 regret 解释为精确最优 gap。",
        "分析启动失败已按原记录保留，恢复后未重跑数值实验；批次完成状态不因已恢复的启动问题改为 failed。"]
    e["parameters"] = {"delta_evaluation_budgets": budgets, "capacity": 30,
        "seeds": [17011, 17027, 17041], "common_support_geometries": summary["common_support_geometries"],
        "same_geometries_reused_across_budgets": summary.get("same_geometries_reused_across_budgets"),
        "algorithms": sorted({r["algorithm"] for r in rows}), "numerical_failures": failures,
        "recovered_analysis_launch_failure": launch, "inference": summary.get("inference")}
    fields = [("mean_relative_regret_pct", "相对同预算算法池 regret", "%", "min",
               "lowest seed-mean cost among these four algorithms at this budget; not an exact optimum", "mean of per-block relative regret after averaging three seeds"),
              ("mean_baseline_improvement_pct", "相对初始化改善", "%", "max",
               "same frozen feasible initialization in each geometry-demand block", "mean per-block improvement after averaging three seeds"),
              ("mean_distance", "平均路线总距离", "synthetic_distance_units", "min",
               "absolute unrounded Euclidean depot-to-depot distance; no vehicle penalty", "mean seed-mean distance over geometry-demand blocks")]
    for index, r in enumerate(rows):
        demand, budget, algorithm = r["demand_mode"], r["budget"], r["algorithm"]
        for field, label, unit, direction, reference, aggregation in fields:
            c = _comparison(field, unit, direction,
                f"budget:8-frozen-geometries:demand={demand}:blocks={r['n_geometry_demand_blocks']}",
                "frozen operator-pair CVRP; strict-improvement acceptance; paired seeds 17011,17027,17041",
                f"{budget} candidate-delta evaluations; accepted complete solution before request B+1", aggregation, reference)
            e["metrics"].append(_metric(f"{demand}-{budget}-{algorithm}-{field}", f"{label} · {demand} · B={budget}",
                algorithm, r.get(field), c, refs["reports/SUMMARY.json"], f"/summary/{index}/{field}"))
    return _save(destination, e)


def _fleet(source: Path, destination: Path, batch: dict, captured: str) -> Path:
    summary, receipt, validation = (_read(source / p) for p in (
        "results/summary.json", "results/supervisor_receipt.json", "validation/full_validation.json"))
    e = _base("fleet", batch["title"], "heterogeneous_fleet", "paired_synthetic_capacity_geometry", captured, "public/research-batches/fleet")
    e["artifacts"], refs = _copy_files(destination, source, batch["files"])
    exit_code = receipt.get("exit_code")
    e["status"] = (_status("completed", summary.get("failed_execution_records")) if exit_code == 0
                   else "failed" if isinstance(exit_code, int) else "unknown")
    e["started_at"], e["finished_at"] = receipt.get("started_utc"), receipt.get("finished_utc")
    e["failures"] = [] if summary.get("failed_execution_records") == 0 else None
    if e["status"] in {"failed", "partial"}:
        e["failure_reason"] = f"Formal numerical exit code={exit_code}; failed execution records={summary.get('failed_execution_records', 'unknown')}"
    e["counts"] = [
        _count("instance", summary.get("recorded_instances"), "formal", "results/summary.json:recorded_instances; six related variants per independent base geometry"),
        _count("geometry", summary.get("base_blocks"), "formal_independent_blocks", "results/summary.json:base_blocks; 24 independent base draws"),
        _count("output", validation.get("formal_heuristic_outputs"), "formal_control", "validation/full_validation.json:formal_heuristic_outputs; not independent solver calls"),
        _count("reference", validation.get("formal_joint_references"), "formal_joint_exact", "validation/full_validation.json:formal_joint_references; exact_all shares computation with two-stage outputs"),
        _count("instance", validation.get("global_feasible"), "globally_feasible_subset", "validation/full_validation.json:global_feasible; common completion-rate denominator"),
    ]
    e["notes"] = [batch["scope"], batch["note"], batch["failures"],
        "完整率使用同一全局可行母集；完成子集 gap 的 cohort 含策略名称，分母不同时禁止直接排名。",
        "UNKNOWN_INCOMPLETE 表示没有得到完整解，不是不可行证明，也不是执行异常。",
        "精确性仅适用于固定的八任务、有限农具和车辆合成合同；576 个输出不等于 576 次独立求解。"]
    e["parameters"] = {"tasks_per_instance": 8, "vehicles": 3, "implements": 4,
        "capacity_pairs": [[5, 5], [3, 7], [1, 9]], "space_variants": ["four_quadrants", "two_clusters"],
        "global_infeasible": validation.get("global_infeasible"),
        "failed_execution_records": summary.get("failed_execution_records"),
        "shared_computation": "exact_all produces joint_exact, two_stage_lex and two_stage_best_tie",
        "cells": [{k: r[k] for k in ("capacity_h", "geometry", "algorithm", "all_instances", "exact_feasible", "complete", "statuses", "gap_n")} for r in summary["cells"]]}
    grouped = defaultdict(list)
    for index, r in enumerate(summary["cells"]):
        grouped[r["algorithm"]].append((index, r))
    protocol = "frozen finite fleet/tool assignment model; 8 tasks; exact reference verified by independent implementation"
    budget = "frozen algorithm rules; no equal-time or equal-evaluation guarantee"
    for algorithm, indexed in grouped.items():
        complete = sum(r["complete"] for _, r in indexed)
        feasible = sum(r["exact_feasible"] for _, r in indexed)
        gap_n = sum(r["gap_n"] for _, r in indexed)
        weighted_gap = sum(r["gap_mean_pct"] * r["gap_n"] for _, r in indexed if r["gap_n"] > 0) / gap_n if gap_n else None
        c = _comparison("complete_rate_pct", "%", "max", f"fleet:all-globally-feasible:{feasible}", protocol, budget,
            "100 × complete instances / same globally feasible instances", "joint exact feasibility; all 144 formal instances retained")
        e["metrics"].append(_metric(f"all-{algorithm}-complete_rate_pct", "完整率 · 全局可行母集", algorithm,
            100 * complete / feasible if feasible else None, c, refs["results/summary.json"],
            f"derived: 100 * sum(/cells[algorithm={algorithm}]/complete) / sum(/cells[algorithm={algorithm}]/exact_feasible)"))
        c = _comparison("complete_subset_gap_pct", "%", "min", f"fleet:completed-subset:strategy={algorithm}:n={gap_n}", protocol, budget,
            "gap_n-weighted mean of cell mean per-instance relative gaps", "joint exact objective on this strategy's completed subset only")
        e["metrics"].append(_metric(f"all-{algorithm}-complete_subset_gap_pct", "完成子集 gap · 不同策略不可直接比较", algorithm,
            weighted_gap, c, refs["results/summary.json"],
            f"derived: sum(/cells[algorithm={algorithm}]/gap_mean_pct * gap_n) / sum(gap_n)"))
    for index, r in enumerate(summary["cells"]):
        algorithm = r["algorithm"]
        cell = f"h={r['capacity_h']}:geometry={r['geometry']}"
        c = _comparison("complete_rate_pct", "%", "max", f"fleet:{cell}:globally-feasible={r['exact_feasible']}", protocol, budget,
            "100 × complete / exact_feasible in this paired cell", "joint exact feasibility in the same paired cell")
        e["metrics"].append(_metric(f"cell-{index}-complete_rate_pct", f"完整率 · {cell}", algorithm,
            100 * r["complete"] / r["exact_feasible"] if r["exact_feasible"] else None, c,
            refs["results/summary.json"], f"derived: 100 * /cells/{index}/complete / /cells/{index}/exact_feasible"))
        c = _comparison("complete_subset_gap_pct", "%", "min", f"fleet:{cell}:completed-subset:strategy={algorithm}:n={r['gap_n']}", protocol, budget,
            "mean per-instance relative gap among complete outputs in this cell", "joint exact objective on this strategy's completed cell subset only")
        e["metrics"].append(_metric(f"cell-{index}-complete_subset_gap_pct", f"完成子集 gap · {cell}", algorithm,
            r.get("gap_mean_pct"), c, refs["results/summary.json"], f"/cells/{index}/gap_mean_pct"))
    return _save(destination, e)


def _turns(source: Path, destination: Path, batch: dict, captured: str) -> Path:
    status, failures = _read(source / "run_status.json"), _read(source / "failures.json")
    with (source / "summary.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    e = _base("turns", batch["title"], "turn_aware_routing", "paired_synthetic_turn_penalty", captured, "public/research-batches/turns")
    e["artifacts"], refs = _copy_files(destination, source, batch["files"])
    e["status"] = _status(status.get("status"), status.get("failures"))
    e["failures"] = [] if status.get("failures") == 0 and failures == [] else None
    if e["status"] in {"failed", "partial"}:
        e["failure_reason"] = f"Recorded route failures: {status.get('failures', 'unknown')}; details in failures.json"
    all_rows = [r for r in rows if r["family"] == "ALL"]
    geometry_counts = {int(r["n"]) for r in all_rows}
    geometry_count = geometry_counts.pop() if len(geometry_counts) == 1 else None
    e["counts"] = [
        _count("route_record", status.get("main_route_records"), "formal", "run_status.json:main_route_records; geometry × lambda × strategy, correlated within geometry"),
        _count("geometry", geometry_count, "formal_independent_blocks", "summary.csv:ALL rows n; five lambda levels reuse the same 30 independent geometries"),
    ]
    e["notes"] = [batch["scope"], batch["note"], batch["failures"],
        "指标按相同 λ、相同几何族和相同候选路径合同匹配比较；未匹配相同计算预算。",
        "精确参考只覆盖预设直角候选路径，不表示连续车辆轨迹可行。",
        "源运行状态没有起止时间字段，两者保留 null，不使用快照采集时间伪造执行时间。",
        "事后平局控制作为独立证据附件保留，未并入预先冻结的五种主策略。"]
    e["parameters"] = {"lambdas": sorted({float(r["lambda"]) for r in rows}),
        "families": sorted({r["family"] for r in rows if r["family"] != "ALL"}),
        "tasks_per_geometry": 8, "strategies": sorted({r["strategy"] for r in rows}),
        "objective": "J = L + lambda * T; T in 90-degree turn equivalents",
        "candidate_paths": "at most two axis-aligned shortest polylines per consecutive service pair",
        "failure_records": failures, "timing_warning": status.get("timing_warning")}
    fields = [("mean_gap_pct", "相对精确候选路径 gap", "%", "mean of per-instance (J - J_oracle) / J_oracle × 100", "joint_dp_oracle for the restricted candidate path model"),
              ("mean_J", "平均联合目标", "synthetic_objective_units", "arithmetic mean across paired geometries", "absolute J=L+lambda*T; no normalization"),
              ("mean_distance", "平均路线长度", "synthetic_length_units", "arithmetic mean across paired geometries", "absolute L; no physical unit or vehicle dynamics"),
              ("mean_turn_quarter_units", "平均转向量", "quarter_turn_units", "arithmetic mean across paired geometries", "unsigned heading changes; 90 degrees = one unit")]
    for index, r in enumerate(rows):
        family, penalty, strategy = r["family"], r["lambda"], r["strategy"]
        for field, label, unit, aggregation, reference in fields:
            c = _comparison(field, unit, "min", f"turns:family={family}:paired-geometries={r['n']}:lambda={penalty}",
                f"frozen 8-task ordering and rectilinear-candidate-path protocol; lambda={penalty}; predefined lexical distance ties",
                "algorithm-specific frozen stopping rules; computation budgets not matched", aggregation, reference)
            e["metrics"].append(_metric(f"row-{index}-{field}", f"{label} · {family} · λ={penalty}", strategy,
                r.get(field), c, refs["summary.csv"], f"CSV row {index + 2}, column {field}; family={family},lambda={penalty},strategy={strategy}"))
    return _save(destination, e)


def _bpp(panel_root: Path, destination: Path) -> Path:
    source = panel_root / "public" / "data"
    meta, catalog = _read(source / "meta.json"), _read(source / "catalog.json")
    run = meta["summary"]["compute"]["run"]
    captured = meta.get("project_validation", {}).get("generatedAt") or meta.get("import_validation", {}).get("created_utc")
    if not captured:
        raise ValueError("Historical BPP snapshot lacks source capture timestamp")
    e = _base("bpp-history", "BPP 前缀选择器 · 历史 768 次运行", "BPP", "historical_prefix_selector", captured, "public/data/meta.json + public/data/catalog.json")
    e["artifacts"], refs = _copy_files(destination, source, [{"path": "meta.json"}, {"path": "catalog.json"}])
    e["status"] = _status(run.get("status"))
    e["finished_at"] = run.get("finished_utc")
    streams = catalog["streams"]
    run_rows = [r for s in streams for r in s.get("runs", [])]
    if len(run_rows) != meta["counts"]["runs"]:
        raise ValueError("Historical BPP catalog run count disagrees with meta.json")
    if len(streams) != meta["counts"]["streams"]:
        raise ValueError("Historical BPP catalog stream count disagrees with meta.json")
    state_counts = defaultdict(int)
    for r in run_rows:
        state_counts[_status(r.get("status"))] += 1
    if e["status"] == "completed" and state_counts["completed"] != len(run_rows):
        e["status"] = "partial"
        e["failure_reason"] = "Historical catalog contains non-completed run records; inspect parameters.recorded_run_states"
    if e["status"] == "failed":
        e["failure_reason"] = str(run.get("failure_reason") or run.get("error") or "Historical run status is failed; no more specific reason is recorded")
    e["counts"] = [
        _count("run", meta["counts"].get("runs"), "historical", "meta.json:counts.runs, cross-checked against catalog run records; no rerun during import"),
        _count("stream", meta["counts"].get("streams"), "historical", "meta.json:counts.streams; train 144, confirmation 108, risk 12"),
        _count("multiset", len({s["group_id"] for s in streams}), "historical", "catalog.json:unique group_id; three correlated orders per group"),
    ]
    e["notes"] = [
        "768 次运行全部是 2026-10-06 的历史策略执行，本次只导入已有元数据与目录，没有运行新实验。",
        "confirmation、risk、train 各自有独立 cohort，不能把训练误差、确认面板或风险反例混为一个平均数。",
        "确认面板为六个固定合成家族；分支 oracle 和 full-run oracle 均是 hindsight 参照，不是在线可实现策略或装箱全局最优。",
        "风险面板保留相同前缀但后缀偏好翻转的负结果；质量变差不表示程序失败。",
        "历史总 900 CPU 秒合规性未确立，不能把未知全流程成本写为零。",
        "本包保留两个已生成索引文件的原字节；索引中的旧站点链接并未自动导入为本后端附件。",
        "prepared_utc 是准备时间而非实测运行起点，因此 started_at 保留 null。",
    ]
    e["parameters"] = {"historical": True, "capacity": meta["protocol"]["capacity"],
        "items_per_stream": meta["protocol"]["n"], "switch_after": meta["protocol"]["switch_after"],
        "families": meta["protocol"]["families"], "streams_by_split": meta["counts"]["streams_by_split"],
        "runs_by_split": meta["counts"]["runs_by_split"], "recorded_run_states": dict(state_counts),
        "historical_total_cpu_compliance": meta.get("historical_audit", {}).get("historical_total_900_cpu_compliance", "unknown")}
    for split, result, locator in (("confirmation", meta["summary"]["confirmation"], "/summary/confirmation"),
                                   ("risk", meta["summary"]["risk"]["summary"], "/summary/risk/summary")):
        cohort = f"historical-bpp-20261006:{split}:streams={result['n']}"
        protocol = f"historical prefix-safe BPP; {split} split; BF shared prefix then fixed branch; freeze namespace={meta['protocol']['namespace']}"
        budget = f"{meta['protocol']['n']} online items; capacity={meta['protocol']['capacity']}; branch decision after={meta['protocol']['switch_after']}"
        for algorithm, value in result["mean_bins"].items():
            c = _comparison("mean_bins", "bins", "min", cohort, protocol, budget,
                "mean bin count over the same split's streams; three orders per multiset correlated", "absolute bin count; hindsight oracles explicitly labeled")
            e["metrics"].append(_metric(f"{split}-{algorithm}-mean_bins", f"平均箱数 · {split}", algorithm,
                value, c, refs["meta.json"], f"{locator}/mean_bins/{algorithm}"))
        for field, label, reference in (
            ("selector_minus_SBS_mean", "选择器减去 SBS", "training-frozen SBS = BF_then_EoH"),
            ("selector_oracle_regret", "两后缀分支 oracle regret", "hindsight minimum of BF and BF_then_EoH after shared BF prefix")):
            c = _comparison(field, "bins", "min", cohort, protocol, budget,
                "mean per-stream paired bin-count difference in the same split", reference)
            e["metrics"].append(_metric(f"{split}-{field}", f"{label} · {split}", "SELECTOR", result.get(field), c,
                refs["meta.json"], f"{locator}/{field}"))
    return _save(destination, e)


def build_packages(output: Path, panel_root: Path) -> list[Path]:
    """Materialize normalized packages from public snapshots; return manifest paths."""
    output, panel_root = Path(output).resolve(), Path(panel_root).resolve()
    source = panel_root / "public" / "research-batches"
    if output.is_relative_to(panel_root):
        raise ValueError("Output must be outside the read-only source panel")
    catalog = _read(source / "catalog.json")
    batches = {b["id"]: b for b in catalog["batches"]}
    paths = [builder(source / name, output / name, batches[name], catalog["capturedAt"])
             for name, builder in (("selector", _selector), ("budget", _budget), ("fleet", _fleet), ("turns", _turns))]
    paths.append(_bpp(panel_root, output / "bpp-history"))
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--panel-root", required=True, type=Path)
    args = parser.parse_args()
    for package in build_packages(args.output, args.panel_root):
        print(package)
