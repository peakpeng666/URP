"""Delivery boundaries and orchestration using isolated non-research fixtures."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


delivery = load("package_delivery")
with patch.dict(sys.modules, package_delivery=delivery):
    rebuild = load("clean_rebuild")


class DeliveryBoundaryTests(unittest.TestCase):
    def test_workspace_input_link_is_materialized_in_delivery_and_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "src/frontend"
            root.mkdir(parents=True)
            inputs = workspace / "data/bpp/inputs"
            inputs.mkdir(parents=True)
            (inputs / "original.zip").write_bytes(b"isolated input fixture")
            (inputs / "unrelated.txt").write_bytes(b"not a delivery input")
            (root / "inputs").symlink_to("../../data/bpp/inputs", target_is_directory=True)
            for collect in (delivery.collect_files, rebuild.source_files):
                files = collect(root)
                self.assertEqual([p.relative_to(root).as_posix() for p in files], ["inputs/original.zip"])
                self.assertEqual(files[0].read_bytes(), b"isolated input fixture")

    def test_workspace_input_exception_rejects_other_and_nested_links(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "src/frontend"
            root.mkdir(parents=True)
            inputs = workspace / "data/bpp/inputs"
            inputs.mkdir(parents=True)
            other = workspace / "unrelated"
            other.mkdir()
            (other / "private.zip").write_bytes(b"not an input")
            link = root / "inputs"
            link.symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                delivery.collect_files(root)
            link.unlink()
            link.symlink_to(inputs, target_is_directory=True)
            (inputs / "nested.zip").symlink_to(other / "private.zip")
            with self.assertRaisesRegex(ValueError, "symlink"):
                delivery.collect_files(root)

    def test_authored_browser_source_and_nested_evidence_are_delivered_without_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            included = {"src/main.tsx", "src/math.test.ts", "vite.config.ts", "package-lock.json",
                        "tools/browser/product-visual.mjs", "tools/browser/package-lock.json",
                        "artifacts/codex-browser/product/replay-390.png", "artifacts/clean_rebuild.json",
                        "artifacts/clean_rebuild_logs/run/01-setup.log", "inputs/original.zip"}
            excluded = {"tools/browser/node_modules/playwright/index.mjs", "node_modules/react/index.js",
                        "public/data/meta.json", "research/MODEL.json", ".venv/bin/python",
                        "dist/index.html", "backups/source.zip", ".env", "scripts/__pycache__/module.pyc"}
            for name in included | excluded:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b"isolated fixture")
            actual = {file.relative_to(root).as_posix() for file in delivery.collect_files(root)}
            self.assertEqual(actual, included)
            copied = {file.relative_to(root).as_posix() for file in rebuild.source_files(root)}
            self.assertEqual(copied, {name for name in included if not name.startswith("artifacts/")})

    def test_missing_source_lockfile_stops_clean_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "package-lock.json"):
                rebuild.validate_sources(Path(directory))

    def test_project_internal_temporary_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside the source project"):
                rebuild.rebuild(root, root, root / "artifacts/report.json", 10, True)

    def test_locked_dependency_manifests_match_both_npm_projects(self):
        for relative in (Path("."), Path("tools/browser")):
            with self.subTest(project=str(relative)):
                package = json.loads((ROOT / relative / "package.json").read_text(encoding="utf-8"))
                lock = json.loads((ROOT / relative / "package-lock.json").read_text(encoding="utf-8"))
                entry = lock["packages"][""]
                for field in ("dependencies", "devDependencies", "engines"):
                    self.assertEqual(package.get(field, {}), entry.get(field, {}))
                for name, dependency in lock["packages"].items():
                    if name and not dependency.get("link"):
                        self.assertTrue(dependency.get("integrity"), f"Missing integrity for {name}")
                        self.assertTrue(dependency.get("resolved", "").startswith("https://"), name)


@unittest.skipUnless(shutil.which("bash"), "Bash is required for the Ubuntu console entrypoint")
class ValidationDispatchTests(unittest.TestCase):
    def test_failure_and_custom_paths_never_refresh_default_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/console.sh", root / "scripts/console.sh")
            fake = root / ".venv/bin/python"
            fake.parent.mkdir(parents=True)
            fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$BPP_TEST_LOG"\n'
                            'if [[ "$1" == scripts/validate_data.py ]]; then exit "${BPP_TEST_EXIT:-0}"; fi\n', encoding="utf-8")
            fake.chmod(0o755)
            (root / "public/data").mkdir(parents=True)
            (root / "public/data/meta.json").write_text("{}", encoding="utf-8")
            log = root / "calls.log"
            scenarios = [
                ([], 23, 23, ["scripts/validate_data.py"]),
                (["--research", "custom"], 0, 0, ["scripts/validate_data.py --research custom"]),
                ([], 0, 0, ["scripts/validate_data.py", "scripts/convert_data.py --refresh-validation"]),
            ]
            for arguments, validator_exit, expected_exit, expected_calls in scenarios:
                with self.subTest(arguments=arguments, exit=validator_exit):
                    log.write_text("", encoding="utf-8")
                    env = dict(os.environ, BPP_TEST_LOG=str(log), BPP_TEST_EXIT=str(validator_exit))
                    result = subprocess.run(["bash", str(root / "scripts/console.sh"), "validate", *arguments],
                                            env=env, capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, expected_exit, result.stderr)
                    self.assertEqual(log.read_text(encoding="utf-8").splitlines(), expected_calls)


if __name__ == "__main__":
    unittest.main()
