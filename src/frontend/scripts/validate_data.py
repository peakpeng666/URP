#!/usr/bin/env python3
"""Read-only validation of the archived experiment; never imports research code.

The only write is the report outside research. Replay consumes recorded
assignments; it does not run policies, fit or tune a model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ATOL = 1e-12
RTOL = 1e-12
ARRAY_FIELDS = ("assignment", "pre_remaining", "post_remaining", "feasible_counts", "used_bins_after", "remaining")
BRANCHES = ("BF", "BF_then_EoH")
CPU_FIELDS = ("cpu_loop_seconds", "cpu_policy_seconds", "cpu_selector_seconds",
              "cpu_instrument_feature_seconds", "cpu_total_including_serialization_seconds")


class ValidationError(ValueError):
    def __init__(self, location, message):
        super().__init__(f"{location}: {message}")
        self.location = location
        self.message = message


def require(condition, location, message):
    if not condition:
        raise ValidationError(location, message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_path(root, relative):
    root = root.resolve()
    path = (root / relative).resolve()
    require(path != root and root in path.parents, str(relative), "path escapes research root")
    return path


def near(actual, expected, location, atol=ATOL, rtol=RTOL):
    a, e = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    require(a.shape == e.shape, location, f"shape {a.shape} != {e.shape}")
    require(np.isfinite(a).all() and np.isfinite(e).all(), location, "non-finite numeric value")
    if not np.allclose(a, e, atol=atol, rtol=rtol):
        difference = np.abs(a - e)
        index = np.unravel_index(np.argmax(difference), difference.shape)
        raise ValidationError(location, f"numeric mismatch at {index}: {a[index]} != {e[index]}; max abs error {difference[index]}")


def features(prefix, remaining, names=None):
    """Independent scalar moments and interpolated quantiles in protocol order."""
    n = len(prefix)
    used = [int(v) for v in remaining if v < 100]
    require(n == 500 and used, "features", "requires 500 prefix items and nonempty used-bin state")
    ordered = sorted(prefix)
    values = {f"item_hist_{i * 10 + 1}_{i * 10 + 10}": sum(i * 10 < v <= (i + 1) * 10 for v in prefix) / n for i in range(10)}
    values.update(item_mean=statistics.mean(prefix) / 100, item_sd=statistics.pstdev(prefix) / 100)
    for q, label in [(0.1, "item_q10"), (0.5, "item_q50"), (0.9, "item_q90")]:
        position = (n - 1) * q
        lo, hi = math.floor(position), math.ceil(position)
        values[label] = (ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)) / 100
    values.update(
        fraction_increase=sum(a < b for a, b in zip(prefix, prefix[1:])) / (n - 1),
        fraction_decrease=sum(a > b for a, b in zip(prefix, prefix[1:])) / (n - 1),
        last100_minus_first100=(statistics.mean(prefix[-100:]) - statistics.mean(prefix[:100])) / 100,
        bins_per_item=len(used) / n,
    )
    values.update({f"residual_hist_{i * 10}_{i * 10 + 9}": sum(i * 10 <= v < (i + 1) * 10 for v in used) / len(used) for i in range(10)})
    values.update(residual_mean=statistics.mean(used) / 100, residual_sd=statistics.pstdev(used) / 100)
    if names is None:
        names = list(values)
    require(len(names) == 31 and set(names) == set(values), "PROTOCOL.json/features/names", "31 known unique feature names required")
    return [values[key] for key in names]


def replay(items, row, arrays, location="trajectory", prefix_length=500):
    """Restore the state from allocations; exact checks include unused slots."""
    n = len(items)
    for field in ARRAY_FIELDS:
        require(field in arrays, f"{location}/{field}", "missing trajectory array")
        data = arrays[field]
        require(data.shape == (n,), f"{location}/{field}", f"expected shape ({n},), got {data.shape}")
        require(data.dtype.kind in "iu", f"{location}/{field}", f"integer dtype required, got {data.dtype}")
    values = {key: arrays[key].tolist() for key in ARRAY_FIELDS}
    remaining = [100] * n
    frequencies = [0] * 101
    frequencies[100] = n
    used = 0
    prefix = None
    consumed = removed = 0
    for step, item in enumerate(items):
        loc = f"{location}/step/{step + 1}"
        target = values["assignment"][step]
        require(0 <= target < n, loc + "/assignment", f"slot {target} outside 0..{n - 1}")
        before = remaining[target]
        after = before - item
        require(0 <= after < 100, loc + "/capacity", f"item {item} in slot {target} with remaining {before}")
        require(values["pre_remaining"][step] == before, loc + "/pre_remaining", f"recorded {values['pre_remaining'][step]} != restored {before}")
        require(values["post_remaining"][step] == after, loc + "/post_remaining", f"recorded {values['post_remaining'][step]} != restored {after}")
        feasible = sum(frequencies[item:])
        require(values["feasible_counts"][step] == feasible, loc + "/feasible_counts", f"recorded {values['feasible_counts'][step]} != {feasible} (all slots)")
        used += before == 100
        require(values["used_bins_after"][step] == used, loc + "/used_bins_after", f"recorded {values['used_bins_after'][step]} != {used}")
        remaining[target] = after
        frequencies[before] -= 1
        frequencies[after] += 1
        consumed += item
        removed += values["pre_remaining"][step] - values["post_remaining"][step]
        require(consumed == removed, loc + "/volume", "cumulative allocated volume != consumed volume")
        if step + 1 == prefix_length:
            prefix = remaining.copy()
    require(values["remaining"] == remaining, location + "/remaining", "final residual state mismatch")
    require(used == row["used_bins"] == sum(v < 100 for v in remaining), location + "/used_bins", "final count mismatch")
    require(sum(100 - v for v in remaining) == sum(items), location + "/volume", "final volume conservation failed")
    require(used >= math.ceil(sum(items) / 100), location + "/volume_lower_bound", "impossible bin count")
    return prefix


def decision(features_vector, model):
    """Frozen-model inference verification only; stable row-index ties."""
    z = (np.asarray(features_vector) - np.asarray(model["mean"])) / np.asarray(model["scale"])
    distances = np.sum((np.asarray(model["x"]) - z) ** 2, axis=1).tolist()
    neighbors = sorted(range(len(distances)), key=lambda i: (distances[i], i))[:model["k"]]
    predictions = [sum(model["y"][i][j] for i in neighbors) / len(neighbors) for j in range(2)]
    selected = model["sbs_index"] if predictions[0] == predictions[1] else int(predictions[1] < predictions[0])
    return {"features": features_vector, "neighbors": neighbors, "squared_distances": [distances[i] for i in neighbors], "predicted_final_bins": predictions, "selected_index": selected}


def summary(rows):
    delta = [r["selector_minus_SBS"] for r in rows]
    headroom = statistics.mean(r["SBS_regret"] for r in rows)
    regret = statistics.mean(r["selector_regret"] for r in rows)
    return {
        "n": len(rows),
        "mean_bins": {k: statistics.mean(r[k] for r in rows) for k in ["BF", "BF_then_EoH", "published_EoH", "SELECTOR", "SBS", "branch_oracle", "full_run_oracle"]},
        "selector_minus_SBS_mean": statistics.mean(delta), "SBS_oracle_headroom": headroom, "selector_oracle_regret": regret,
        "headroom_recovered_fraction": None if headroom == 0 else (headroom - regret) / headroom,
        "W_T_L_vs_SBS": [sum(v < 0 for v in delta), sum(v == 0 for v in delta), sum(v > 0 for v in delta)],
        "worst_harm_vs_SBS": max(delta), "best_gain_vs_SBS": -min(delta),
        "choices": {k: sum(r["selected_branch"] == k for r in rows) for k in BRANCHES},
        "oracle_preferences": {k: sum(r["oracle_preferred"] == k for r in rows) for k in [*BRANCHES, "tie"]},
    }


def compare_tree(actual, expected, location):
    if isinstance(expected, dict):
        require(isinstance(actual, dict), location, "object required")
        for key, value in expected.items():
            require(key in actual, location + "/" + key, "missing key")
            compare_tree(actual[key], value, location + "/" + key)
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        near(actual, expected, location)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), location, "list length/type mismatch")
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare_tree(a, e, f"{location}/{i}")
    else:
        require(actual == expected, location, f"{actual!r} != {expected!r}")


def compare_csv(path, expected, keys):
    with path.open(encoding="utf-8", newline="") as handle:
        actual = list(csv.DictReader(handle))
    index = {tuple(row[k] for k in keys): row for row in actual}
    require(len(actual) == len(expected) == len(index), str(path), "row count or unique key mismatch")
    for row in expected:
        key = tuple(str(row[k]) for k in keys)
        require(key in index, str(path), f"missing row {key}")
        for field, value in row.items():
            location = f"{path.name}/{':'.join(key)}/{field}"
            require(field in index[key], location, "missing column")
            stored = index[key][field]
            if isinstance(value, (int, float)):
                near(float(stored), value, location)
            else:
                require(stored == value, location, f"{stored!r} != {value!r}")


class Validator:
    def __init__(self, root):
        self.root = root.resolve()
        self.report = {
            "schemaVersion": 1, "status": "RUNNING", "passed": False,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
            "coverage": {k: 0 for k in ["inputs", "runs", "trajectorySteps", "selectorDecisions", "commonPrefixes", "riskGroups", "confirmationCells", "bootstrapReplicates", "manifestEntries", "freezeHashes"]},
            "tolerances": {"integerArraysCountsAndHashes": "exact", "floatingPointAbsolute": ATOL, "floatingPointRelative": RTOL, "bootstrap": "stored indices replayed; no new resampling"},
            "checks": [], "failures": [], "metrics": {},
            "limitations": [
                "This project restores all recorded allocations, checks state invariants and frozen-selector arithmetic; it does not re-run policy scoring or certify policy optimality.",
                "Historical package audit and this project validation are separate. Historical total 900 CPU-second budget cannot be certified; interrupted validator and cached rerun remain historical limitations.",
                "No new model fitting, training, policy experiments or random bootstrap draws are performed. Historical bootstrap indices are reused.",
                "Browser, mobile, physical-device, accessibility and native-Ubuntu acceptance are outside this scientific-data report.",
                "Hash equality demonstrates consistency with the delivered manifest/freeze, not independent authorship, timestamp attestation or universal online-information isolation.",
            ],
        }
        self.coverage = self.report["coverage"]
        self.rows = []
        self.cpu_rows = []
        self.train_features = {}
        self.risk = defaultdict(list)

    def integrity(self):
        manifest = read_json(self.root / "MANIFEST.json")
        files = manifest["files"]
        require(len(files) == 1914, "MANIFEST.json/files", "expected 1914 manifest entries")
        for name, meta in files.items():
            path = safe_path(self.root, name)
            payload = path.read_bytes()
            require(len(payload) == meta["bytes"], name, "manifest byte length mismatch")
            require(digest(payload) == meta["sha256"], name, "manifest SHA256 mismatch")
            self.coverage["manifestEntries"] += 1
        frozen_bytes = (self.root / "FREEZE.json").read_bytes()
        require(digest(frozen_bytes) == manifest["scientific_freeze_sha256"], "FREEZE.json", "manifest scientific freeze SHA256 mismatch")
        frozen = json.loads(frozen_bytes)
        for name, expected in frozen["files"].items():
            require(digest(safe_path(self.root, name).read_bytes()) == expected, name, "FREEZE SHA256 mismatch")
            self.coverage["freezeHashes"] += 1
        self.protocol = read_json(self.root / "PROTOCOL.json")
        self.model = read_json(self.root / "MODEL.json")
        self.model_freeze = read_json(self.root / "MODEL_FREEZE.json")
        require(digest((self.root / "MODEL.json").read_bytes()) == self.model_freeze["model_sha256"], "MODEL.json", "MODEL_FREEZE SHA256 mismatch")
        for policy, expected in self.protocol["policy_hashes"].items():
            require(digest((self.root / "sources" / f"{policy}.py.txt").read_bytes()) == expected, f"sources/{policy}.py.txt", "protocol source hash mismatch")
        self.report["sourceHashes"] = {name: digest((self.root / name).read_bytes()) for name in ["MANIFEST.json", "FREEZE.json", "MODEL.json", "MODEL_FREEZE.json", "PROTOCOL.json"]}

    def streams(self):
        p, m, mf = self.protocol, self.model, self.model_freeze
        require(p["n"] == 5000 and p["capacity"] == 100 and p["switch_after"] == 500, "PROTOCOL.json", "unexpected n/capacity/switch")
        require(p["branches"] == list(BRANCHES) and m["k"] == p["selector"]["k"] == 5, "MODEL.json/k", "unexpected branches or k")
        require(len(p["instances"]) == 264, "PROTOCOL.json/instances", "expected 264 streams")
        require(len({v["instance_id"] for v in p["instances"]}) == 264, "PROTOCOL.json/instances", "duplicate ID")
        expected_json, expected_npz = set(), set()
        groups = defaultdict(list)
        for meta in p["instances"]:
            iid = meta["instance_id"]
            location = f"inputs/{iid}.json"
            data = read_json(self.root / location)
            for key, value in meta.items():
                require(data.get(key) == value, location + "/" + key, "input metadata differs from protocol")
            items = data["items"]
            require(len(items) == data["n"] == 5000 and data["capacity"] == 100, location, "input dimensions mismatch")
            require(all(type(v) is int and 1 <= v <= 100 for v in items), location + "/items", "items must be integers 1..100")
            require(digest(canonical(sorted(items))) == data["multiset_sha256"], location + "/multiset_sha256", "sorted items hash mismatch")
            source = data.get("source_position")
            if meta["split"] == "risk":
                require(source is None, location + "/source_position", "risk records have no source-position mapping")
                require(digest(canonical(items[:500])) == data["prefix_sha256"], location + "/prefix_sha256", "risk prefix hash mismatch")
            else:
                require(isinstance(source, list) and sorted(source) == list(range(5000)), location + "/source_position", "not a permutation of 0..4999")
            groups[(meta["split"], meta["group_id"])].append(data)
            self.coverage["inputs"] += 1
            policies = list(BRANCHES) if meta["split"] == "train" else [*BRANCHES, "published_EoH", "SELECTOR"]
            rows, trajectories, states, fs = {}, {}, {}, {}
            for policy in policies:
                raw_name = f"raw/{iid}__{policy}.json"
                row = read_json(self.root / raw_name)
                require(row["instance_id"] == iid and row["policy"] == policy, raw_name, "run identity mismatch")
                require(row["status"] == "complete" and row["steps"] == 5000 and row.get("error") is None, raw_name, "run not complete/error present")
                require(type(row["used_bins"]) is int and 1 <= row["used_bins"] <= 5000, raw_name + "/used_bins", "invalid final count type/range")
                if policy != "SELECTOR":
                    require(row["branch"] == policy, raw_name + "/branch", "fixed-policy branch differs from policy")
                cpu = {key: row[key] for key in CPU_FIELDS}
                require(all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in cpu.values()), raw_name + "/cpu", "non-finite/negative CPU component")
                self.cpu_rows.append({"split": meta["split"], "policy": policy, **cpu})
                require(row["items_sha256"] == digest(canonical(items)), raw_name + "/items_sha256", "ordered items hash mismatch")
                archive = safe_path(self.root, row["trajectory_file"])
                require(archive == (self.root / f"raw/{iid}__{policy}.npz").resolve(), raw_name + "/trajectory_file", "unexpected trajectory path")
                require(digest(archive.read_bytes()) == row["trajectory_sha256"], raw_name + "/trajectory_sha256", "trajectory hash mismatch")
                with np.load(archive, allow_pickle=False) as z:
                    arrays = {k: z[k] for k in z.files}
                state = replay(items, row, arrays, row["trajectory_file"])
                require(digest(canonical(state)) == row["prefix_remaining_sha256"], raw_name + "/prefix_remaining_sha256", "restored prefix state hash mismatch")
                fs[policy] = features(items[:500], state, p["features"]["names"])
                near(row["prefix_features"], fs[policy], raw_name + "/prefix_features")
                rows[policy], trajectories[policy], states[policy] = row, arrays, state
                expected_json.add(Path(raw_name).name)
                expected_npz.add(archive.name)
                self.coverage["runs"] += 1
                self.coverage["trajectorySteps"] += 5000
            for policy in ["BF_then_EoH"] + (["SELECTOR"] if "SELECTOR" in rows else []):
                require(states[policy] == states["BF"], iid + "/common_prefix", f"{policy} prefix state differs from BF")
                for field in ARRAY_FIELDS[:-1]:
                    require(np.array_equal(trajectories[policy][field][:500], trajectories["BF"][field][:500]), iid + "/common_prefix/" + field, policy + " prefix differs from BF")
            self.coverage["commonPrefixes"] += 1
            bins = {policy: row["used_bins"] for policy, row in rows.items()}
            oracle = min(bins[b] for b in BRANCHES)
            expected = {k: meta[k] for k in ["instance_id", "group_id", "split", "family", "replicate", "order"]}
            expected.update(bins)
            expected.update(SBS=bins[mf["training_sbs"]], branch_oracle=oracle,
                            oracle_preferred="tie" if bins["BF"] == bins["BF_then_EoH"] else min(BRANCHES, key=lambda k: bins[k]),
                            SBS_regret=bins[mf["training_sbs"]] - oracle)
            if meta["split"] == "train":
                self.train_features[iid] = fs["BF"]
            else:
                chosen = rows["SELECTOR"]
                branch = chosen["branch"]
                require(branch in BRANCHES and chosen["selector_consumed_count"] == 500, iid + "/SELECTOR", "invalid branch or decision boundary")
                for field in ARRAY_FIELDS:
                    require(np.array_equal(trajectories["SELECTOR"][field], trajectories[branch][field]), iid + "/SELECTOR/" + field, "not identical to chosen continuation")
                computed = decision(fs["SELECTOR"], m)
                compare_tree(chosen["decision"], computed, iid + "/SELECTOR/decision")
                require(BRANCHES[computed["selected_index"]] == branch, iid + "/SELECTOR/branch", "selected_index branch mismatch")
                self.coverage["selectorDecisions"] += 1
                expected.update(selected_branch=branch, selector_minus_SBS=bins["SELECTOR"] - expected["SBS"], selector_regret=bins["SELECTOR"] - oracle,
                                full_run_oracle=min(bins["BF"], bins["published_EoH"]), selector_minus_full_EoH=bins["SELECTOR"] - bins["published_EoH"])
                if meta["split"] == "risk":
                    self.risk[meta["group_id"]].append({"prefix": items[:500], "state": states["BF"], "decision": chosen["decision"], "branch": branch})
            self.rows.append(expected)
            if self.coverage["inputs"] % 24 == 0:
                print(f"Validated {self.coverage['inputs']}/264 inputs; {self.coverage['runs']}/768 runs", flush=True)
        require({path.name for path in (self.root / "inputs").glob("*.json")} == {meta["instance_id"] + ".json" for meta in p["instances"]}, "inputs", "extra/missing input JSON")
        require({path.name for path in (self.root / "raw").glob("*.json")} == expected_json, "raw", "extra/missing raw JSON")
        require({path.name for path in (self.root / "raw").glob("*.npz")} == expected_npz, "raw", "extra/missing trajectory NPZ")
        require(Counter(r["split"] for r in self.rows) == {"train": 144, "confirmation": 108, "risk": 12}, "streams/splits", "split counts mismatch")
        expected_counts = {
            "train_groups": 48, "train_streams": 144, "train_label_runs": 288,
            "confirmation_groups": 36, "confirmation_streams": 108, "confirmation_runs": 432,
            "risk_groups": 4, "risk_streams": 12, "risk_runs": 48, "total_full_policy_stream_runs": 768,
        }
        compare_tree(p["counts"], expected_counts, "PROTOCOL.json/counts")
        require(Counter(split for split, _ in groups) == {"train": 48, "confirmation": 36, "risk": 4}, "groups", "actual split group counts mismatch")
        group_hashes = defaultdict(set)
        for (split, group), entries in groups.items():
            require(len(entries) == 3 and {r["order"] for r in entries} == set(p["orders"]), group, "three-order group incomplete")
            require(len({r["multiset_sha256"] for r in entries}) == 1, group, "group multiset differs")
            bases = []
            for entry in entries:
                if split == "risk":
                    base = entry["items"][:500] + sorted(entry["items"][500:])
                else:
                    base = [None] * 5000
                    for value, source in zip(entry["items"], entry["source_position"]):
                        base[source] = value
                bases.append(base)
                portion = entry["items"][500:] if split == "risk" else entry["items"]
                if entry["order"] != "random":
                    require(portion == sorted(portion, reverse=entry["order"] == "descending"), group + "/" + entry["order"], "arrival order not monotone")
            require(bases[0] == bases[1] == bases[2], group + "/source_position", "permutations do not recover common source")
            group_hashes[split].add(entries[0]["multiset_sha256"])
        for a, b in [("train", "confirmation"), ("train", "risk"), ("confirmation", "risk")]:
            require(not group_hashes[a] & group_hashes[b], "split_disjointness", f"{a}/{b} share an input multiset")

    def frozen_model_and_risk(self):
        model, frozen = self.model, self.model_freeze
        rows = [r for r in self.rows if r["split"] == "train"]
        require([r["instance_id"] for r in rows] == frozen["training_rows"], "MODEL_FREEZE.json/training_rows", "training order differs from protocol")
        x = np.asarray([self.train_features[r["instance_id"]] for r in rows])
        y = np.asarray([[r[b] for b in BRANCHES] for r in rows])
        means, scales = x.mean(axis=0), x.std(axis=0, ddof=0)
        scales[scales == 0] = 1
        near(model["mean"], means, "MODEL.json/mean")
        near(model["scale"], scales, "MODEL.json/scale")
        near(model["x"], (x - means) / scales, "MODEL.json/x")
        require(np.array_equal(model["y"], y) and np.array_equal(frozen["training_labels"], y), "MODEL.json/y", "labels differ from real training runs")
        sbs = int(np.argmin(y.mean(axis=0)))
        require(sbs == model["sbs_index"] and BRANCHES[sbs] == frozen["training_sbs"], "MODEL.json/sbs_index", "SBS not lowest training mean branch")
        near(frozen["training_mean_bins"], y.mean(axis=0), "MODEL_FREEZE.json/training_mean_bins")
        near(frozen["training_oracle_mean_bins"], y.min(axis=1).mean(), "MODEL_FREEZE.json/training_oracle_mean_bins")
        require(len(self.risk) == 4, "risk", "expected four groups")
        for group, entries in self.risk.items():
            require(len(entries) == 3 and entries[0] == entries[1] == entries[2], "risk/" + group, "prefix/state/features/prediction/choice must match across futures")
            self.coverage["riskGroups"] += 1

    def analyses(self):
        stored = read_json(self.root / "analysis/SUMMARY.json")
        splits = {s: [r for r in self.rows if r["split"] == s] for s in ["train", "confirmation", "risk"]}
        for split, rows in splits.items():
            compare_csv(self.root / f"analysis/{split}_per_stream.csv", rows, ["instance_id"])
        cpu_totals = []
        for split in splits:
            for policy in [*BRANCHES, "published_EoH", "SELECTOR"]:
                rows = [r for r in self.cpu_rows if r["split"] == split and r["policy"] == policy]
                if rows:
                    cpu_totals.append({"split": split, "policy": policy, "runs": len(rows),
                                       **{key: sum(r[key] for r in rows) for key in CPU_FIELDS}})
        compare_csv(self.root / "analysis/cpu_accounting.csv", cpu_totals, ["split", "policy"])
        confirmation, risk_summary = summary(splits["confirmation"]), summary(splits["risk"])
        compare_tree(stored["confirmation"], confirmation, "analysis/SUMMARY.json/confirmation")
        compare_tree(stored["risk"]["summary"], risk_summary, "analysis/SUMMARY.json/risk/summary")
        training = {
            "n": len(splits["train"]), "sbs": self.model_freeze["training_sbs"],
            "mean_bins": [statistics.mean(r[b] for r in splits["train"]) for b in BRANCHES],
            "branch_oracle_mean": statistics.mean(r["branch_oracle"] for r in splits["train"]),
            "SBS_oracle_headroom": statistics.mean(r["SBS_regret"] for r in splits["train"]),
        }
        compare_tree(stored["training"], training, "analysis/SUMMARY.json/training")
        risk_groups = []
        for group in sorted(self.risk):
            rows = [r for r in splits["risk"] if r["group_id"] == group]
            preferences = [r["oracle_preferred"] for r in rows]
            risk_groups.append({"group": group, "choice": rows[0]["selected_branch"], "oracle_preferences": preferences,
                                "selector_regrets": [r["selector_regret"] for r in rows], "oracle_preference_reverses": set(BRANCHES).issubset(preferences)})
        compare_tree(stored["risk"]["groups"], risk_groups, "analysis/SUMMARY.json/risk/groups")
        cells = []
        for family in self.protocol["families"]:
            for order in self.protocol["orders"]:
                rows = [r for r in splits["confirmation"] if r["family"] == family and r["order"] == order]
                require(len(rows) == 6, family + "/" + order, "expected six confirmation groups per cell")
                s = summary(rows)
                cells.append({"family": family, "order": order, "n": s["n"], **s["mean_bins"],
                              "selector_minus_SBS": s["selector_minus_SBS_mean"], "SBS_headroom": s["SBS_oracle_headroom"], "selector_regret": s["selector_oracle_regret"],
                              "BF_selections": s["choices"]["BF"], "EoH_selections": s["choices"]["BF_then_EoH"],
                              "wins": s["W_T_L_vs_SBS"][0], "ties": s["W_T_L_vs_SBS"][1], "losses": s["W_T_L_vs_SBS"][2]})
        compare_csv(self.root / "analysis/family_order_summary.csv", cells, ["family", "order"])
        self.coverage["confirmationCells"] = len(cells)
        group_deltas = np.asarray([[statistics.mean(r["selector_minus_SBS"] for r in splits["confirmation"] if r["family"] == family and r["replicate"] == rep) for rep in range(6)] for family in self.protocol["families"]])
        with np.load(self.root / "analysis/cluster_bootstrap.npz", allow_pickle=False) as z:
            indices, archived_boots, archived_groups = z["indices"], z["mean_deltas"], z["group_deltas"]
        require(indices.shape == (10000, 6, 6) and indices.dtype.kind in "iu" and np.all((indices >= 0) & (indices < 6)), "cluster_bootstrap.npz/indices", "invalid stratified cluster index array")
        near(archived_groups, group_deltas, "cluster_bootstrap.npz/group_deltas")
        boots = np.take_along_axis(group_deltas[None, :, :], indices, axis=2).mean(axis=(1, 2))
        near(archived_boots, boots, "cluster_bootstrap.npz/mean_deltas")
        ordered = np.sort(boots)
        ci = []
        for q in (0.025, 0.975):
            position = (len(boots) - 1) * q
            lo, hi = math.floor(position), math.ceil(position)
            ci.append(float(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)))
        near(stored["confirmation"]["cluster_bootstrap_95_percentile_CI"], ci, "SUMMARY.json/confirmation/cluster_bootstrap_95_percentile_CI")
        expected_seed = int.from_bytes(hashlib.sha256((self.protocol["namespace"] + "|bootstrap").encode()).digest()[:16], "big")
        require(stored["bootstrap"]["seed"] == expected_seed and stored["bootstrap"]["replicates"] == len(boots), "SUMMARY.json/bootstrap", "seed metadata/count mismatch")
        self.coverage["bootstrapReplicates"] = len(boots)
        confirmation["cluster_bootstrap_95_percentile_CI"] = ci
        self.report["metrics"] = {"training": training, "confirmation": confirmation, "risk": {"summary": risk_summary, "groups": risk_groups}}

    def run(self):
        start = time.monotonic()
        stages = [("delivered_manifest_and_freeze_hashes", self.integrity), ("all_inputs_and_recorded_trajectories", self.streams),
                  ("frozen_model_and_same_prefix_risk", self.frozen_model_and_risk), ("csv_summaries_cells_and_cluster_bootstrap", self.analyses)]
        for name, method in stages:
            stage_start = time.monotonic()
            try:
                method()
                self.report["checks"].append({"name": name, "status": "PASS", "seconds": round(time.monotonic() - stage_start, 3)})
            except Exception as exc:
                self.report["failures"].append({"check": name, "location": getattr(exc, "location", name), "message": str(exc), "type": type(exc).__name__})
                self.report["checks"].append({"name": name, "status": "FAIL", "seconds": round(time.monotonic() - stage_start, 3)})
                break
        self.report["passed"] = not self.report["failures"] and len(self.report["checks"]) == len(stages)
        self.report["status"] = "PASS" if self.report["passed"] else "FAIL"
        self.report["elapsedSeconds"] = round(time.monotonic() - start, 3)
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=ROOT / "research")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/validation_report.json")
    args = parser.parse_args()
    research, output = args.research.resolve(), args.output.resolve()
    require(output != research and research not in output.parents, str(output), "report must be outside immutable research directory")
    report = Validator(research).run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "coverage": report["coverage"], "elapsedSeconds": report["elapsedSeconds"], "failures": report["failures"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
