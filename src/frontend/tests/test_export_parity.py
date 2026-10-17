"""Every real export must remain byte-linked and scientifically equal to its source.

No skip/fallback fixtures: run data-convert first. This does not execute policies,
train a model, modify research, or rewrite the scientific validation report.
"""
import csv
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
OUTPUT = ROOT / "public/data"
BRANCHES = ("BF", "BF_then_EoH")
ARRAYS = ("assignment", "pre_remaining", "post_remaining", "feasible_counts", "used_bins_after", "remaining")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExportParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Missing required data raises an error, never a misleading skipped PASS.
        cls.manifest = read(RESEARCH / "MANIFEST.json")["files"]
        cls.protocol = read(RESEARCH / "PROTOCOL.json")
        cls.model = read(RESEARCH / "MODEL.json")
        cls.freeze = read(RESEARCH / "MODEL_FREEZE.json")
        cls.catalog = read(OUTPUT / "catalog.json")
        cls.streams = cls.catalog["streams"]
        cls.source_inputs = {
            meta["instance_id"]: read(RESEARCH / "inputs" / (meta["instance_id"] + ".json"))
            for meta in cls.protocol["instances"]
        }
        cls.checked_evidence = set()

    def assert_original_fields(self, derived, original, location):
        """Recursively preserve originals, allowing only documented JS seed strings."""
        if isinstance(original, dict):
            self.assertIsInstance(derived, dict, location)
            for key, value in original.items():
                self.assertIn(key, derived, location)
                self.assert_original_fields(derived[key], value, location + "/" + key)
        elif isinstance(original, list):
            self.assertIsInstance(derived, list, location)
            self.assertEqual(len(derived), len(original), location)
            for i, (actual, expected) in enumerate(zip(derived, original)):
                self.assert_original_fields(actual, expected, f"{location}/{i}")
        elif type(original) is int and abs(original) > 2**53 - 1:
            self.assertIsInstance(derived, str, location)
            self.assertEqual(derived, str(original), location)
        else:
            self.assertEqual(type(derived), type(original), location)
            self.assertEqual(derived, original, location)

    def assert_source(self, descriptor, relative):
        self.assertEqual(descriptor["path"], relative)
        self.assertEqual(descriptor["url"], "/data/evidence/" + relative)
        original_path = RESEARCH / relative
        expected = self.manifest.get(relative)
        if relative == "MANIFEST.json":
            expected = {"bytes": original_path.stat().st_size, "sha256": sha(original_path)}
        self.assertIsNotNone(expected, f"{relative} is not in original manifest")
        self.assertEqual(descriptor["sha256"], expected["sha256"], relative)
        self.assertEqual(descriptor["bytes"], expected["bytes"], relative)
        if relative not in self.checked_evidence:
            exported = OUTPUT / "evidence" / relative
            self.assertEqual(exported.stat().st_size, expected["bytes"], relative)
            self.assertEqual(sha(exported), expected["sha256"], relative)
            self.checked_evidence.add(relative)

    def test_264_input_shards_and_catalog_groups(self):
        self.assertEqual(self.catalog["schema_version"], 1)
        self.assertEqual(len(self.streams), 264)
        self.assertEqual({r["instance_id"] for r in self.streams}, set(self.source_inputs))
        self.assertEqual({p.stem for p in (OUTPUT / "inputs").glob("*.json")}, set(self.source_inputs))
        expected_decisions = set()
        csv_index = {}
        for split in ("train", "confirmation", "risk"):
            with (RESEARCH / "analysis" / f"{split}_per_stream.csv").open(newline="", encoding="utf-8") as file:
                csv_index.update({r["instance_id"]: r for r in csv.DictReader(file)})
        for stream in self.streams:
            iid = stream["instance_id"]
            with self.subTest(instance=iid):
                original = self.source_inputs[iid]
                derived = read(OUTPUT / "inputs" / (iid + ".json"))
                self.assertEqual(derived["schema_version"], 1)
                self.assert_original_fields(derived, original, iid)
                self.assert_source(derived["source"], f"inputs/{iid}.json")
                self.assert_source(stream["source"], f"inputs/{iid}.json")
                self.assertEqual(stream["input_url"], f"/data/inputs/{iid}.json")
                for key in ("instance_id", "group_id", "family", "split", "order", "replicate", "n", "capacity", "multiset_sha256"):
                    self.assertEqual(stream[key], original[key], f"{iid}/{key}")
                policies = list(BRANCHES) if original["split"] == "train" else [*BRANCHES, "published_EoH", "SELECTOR"]
                self.assertEqual(len(stream["runs"]), len(policies))
                self.assertEqual({r["policy"] for r in stream["runs"]}, set(policies))
                self.assertEqual({r["run_id"] for r in stream["runs"]}, {iid + "__" + policy for policy in policies})
                if original["split"] == "train":
                    self.assertIsNone(stream["decision_url"])
                else:
                    expected_decisions.add(iid)
                    self.assertEqual(stream["decision_url"], f"/data/decisions/{iid}.json")
                self.assertEqual(set(stream["results"]), set(csv_index[iid]))
                for field, raw_value in csv_index[iid].items():
                    actual = stream["results"][field]
                    if type(actual) in (int, float):
                        self.assertEqual(float(raw_value), actual, f"{iid}/results/{field}")
                    else:
                        self.assertEqual(raw_value, actual, f"{iid}/results/{field}")
        self.assertEqual(len(expected_decisions), 120)
        self.assertEqual({p.stem for p in (OUTPUT / "decisions").glob("*.json")}, expected_decisions)

    def test_all_768_runs_hashlinks_raw_fields_and_six_arrays(self):
        descriptors = [descriptor for stream in self.streams for descriptor in stream["runs"]]
        self.assertEqual(len(descriptors), 768)
        ids = {r["run_id"] for r in descriptors}
        self.assertEqual(len(ids), 768)
        self.assertEqual({p.stem for p in (OUTPUT / "runs").glob("*.json")}, ids)
        self.assertEqual({p.stem for p in (RESEARCH / "raw").glob("*.json")}, ids)
        decisions = 0
        for descriptor in descriptors:
            run_id = descriptor["run_id"]
            with self.subTest(run=run_id):
                exported_path = OUTPUT / "runs" / (run_id + ".json")
                self.assertEqual(descriptor["data_url"], f"/data/runs/{run_id}.json")
                self.assertEqual(sha(exported_path), descriptor["sha256"], run_id)
                run = read(exported_path)
                raw = read(RESEARCH / "raw" / (run_id + ".json"))
                self.assert_original_fields(run, raw, run_id)
                self.assertEqual(run["schema_version"], 1)
                self.assertEqual(run["run_id"], run_id)
                iid = raw["instance_id"]
                self.assertEqual(run["items"], self.source_inputs[iid]["items"], run_id)
                self.assertEqual(run["capacity"], self.source_inputs[iid]["capacity"], run_id)
                for key in ("policy", "branch", "used_bins", "status", "steps"):
                    self.assertEqual(descriptor[key], raw[key], run_id + "/" + key)
                expected_sources = {
                    "input": f"inputs/{iid}.json", "record": f"raw/{run_id}.json",
                    "trajectory": raw["trajectory_file"], "model": "MODEL.json",
                    "protocol": "PROTOCOL.json", "freeze": "MODEL_FREEZE.json",
                }
                self.assertEqual(set(run["source"]), set(expected_sources))
                self.assertEqual(descriptor["source"], run["source"])
                for role, relative in expected_sources.items():
                    self.assert_source(run["source"][role], relative)
                self.assertEqual(run["source"]["trajectory"]["sha256"], raw["trajectory_sha256"])
                with np.load(RESEARCH / raw["trajectory_file"], allow_pickle=False) as archive:
                    self.assertEqual(set(archive.files), set(ARRAYS))
                    for field in ARRAYS:
                        self.assertEqual(len(run[field]), 5000, run_id + "/" + field)
                        self.assertTrue(all(type(v) is int for v in run[field]), run_id + "/" + field)
                        self.assertEqual(run[field], archive[field].tolist(), run_id + "/" + field)
                if raw["policy"] == "SELECTOR":
                    decisions += 1
                    decision = read(OUTPUT / "decisions" / (iid + ".json"))
                    self.assert_original_fields(decision, raw["decision"], iid + "/decision")
                    self.assertEqual(decision["source"], run["source"])
                    self.assertEqual(decision["schema_version"], 1)
                    self.assertEqual(decision["instance_id"], iid)
                    self.assertEqual(decision["selector_consumed_count"], 500)
                    self.assertEqual(decision["feature_names"], self.protocol["features"]["names"])
                    self.assertEqual(run["decision"]["feature_names"], decision["feature_names"])
                    self.assertEqual(run["decision"]["neighbor_rows"], decision["neighbor_rows"])
                    self.assertEqual(len(decision["neighbor_rows"]), 5)
                    for position, neighbor in enumerate(decision["neighbor_rows"]):
                        index = raw["decision"]["neighbors"][position]
                        neighbor_id = self.freeze["training_rows"][index]
                        self.assertEqual(neighbor["index"], index)
                        self.assertEqual(neighbor["instance_id"], neighbor_id)
                        self.assertEqual(neighbor["family"], self.source_inputs[neighbor_id]["family"])
                        self.assertEqual(neighbor["order"], self.source_inputs[neighbor_id]["order"])
                        self.assertEqual(neighbor["labels"], self.model["y"][index])
                        self.assertEqual(neighbor["squared_distance"], raw["decision"]["squared_distances"][position])
                        self.assert_source(neighbor["source"], f"inputs/{neighbor_id}.json")
        self.assertEqual(decisions, 120)

    def test_exported_metadata_summaries_model_validation_and_evidence(self):
        meta = read(OUTPUT / "meta.json")
        self.assertEqual(meta["schema_version"], 1)
        self.assertEqual(meta["counts"], {
            "streams": 264, "runs": 768,
            "streams_by_split": {"train": 144, "confirmation": 108, "risk": 12},
            "runs_by_split": {"train": 288, "confirmation": 432, "risk": 48},
        })
        self.assert_original_fields(meta["summary"], read(RESEARCH / "analysis/SUMMARY.json"), "meta/summary")
        self.assert_original_fields(meta["model"], self.model, "meta/model")
        self.assert_original_fields(meta["protocol"], {k: v for k, v in self.protocol.items() if k != "instances"}, "meta/protocol")
        self.assertEqual(meta["training_rows"], self.freeze["training_rows"])
        self.assertEqual(meta["historical_audit"], read(RESEARCH / "independent_audit/FINAL_AUDIT.json"))
        for relative, descriptor in meta["sources"].items():
            self.assert_source(descriptor, relative)
        # Shared-workspace exports were rebuilt in data/bpp/audit. The older
        # standalone frontend report remains historical evidence, so do not
        # require a newer export to impersonate that older run's timestamp.
        project_validation = read(OUTPUT / "validation.json")
        report_paths = [ROOT / "artifacts/validation_report.json"]
        shared_audit = ROOT.parents[1] / "data/bpp/audit/validation_report.json"
        if OUTPUT.resolve() == (ROOT.parents[1] / "data/bpp/exports").resolve():
            report_paths.append(shared_audit)
        known_reports = [read(path) for path in report_paths if path.is_file()]
        self.assertIn(project_validation, known_reports, "Export validation must match a retained source report")
        self.assertEqual(meta["project_validation"], project_validation)
        self.assertEqual(read(OUTPUT / "validation.json"), project_validation)
        self.assertEqual(project_validation["status"], "PASS", "Full real-data parity requires completed scientific validation")
        self.assertTrue(project_validation["passed"])
        for relative, expected_hash in project_validation["sourceHashes"].items():
            self.assertEqual(sha(RESEARCH / relative), expected_hash, relative)
        cells = read(OUTPUT / "cells.json")
        self.assertEqual(cells["schema_version"], 1)
        self.assertEqual(len(cells["cells"]), 18)
        self.assert_source(cells["source"], "analysis/family_order_summary.csv")
        with (RESEARCH / "analysis/family_order_summary.csv").open(newline="", encoding="utf-8") as file:
            source_cells = list(csv.DictReader(file))
        for derived, original in zip(cells["cells"], source_cells):
            self.assertEqual(set(derived), set(original))
            for key, value in original.items():
                self.assertEqual(derived[key], value if key in ("family", "order") else float(value))


if __name__ == "__main__":
    unittest.main()
