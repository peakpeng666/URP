"""Package a portable source delivery from an explicit allowlist, with integrity manifest.

Never packages generated research/data, virtual environments, node_modules or secrets.
The original immutable input ZIP is included. Rebuild generated data after extraction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INPUT_SHA256 = "5f47d49fade8f926bb5751818b038288a772b711d4249d70a7a392eeb9719350"
SOURCE_DIRS = {"src", "app", "core", "scripts", "tests", "docs", "handoff", "public", "preview",
               "assets", "components", "lib", "pages", "styles"}
ROOT_FILES = {"README.md", "LICENSE", "LICENSE.md", "package.json", "package-lock.json",
              "requirements.lock", ".gitignore", ".nvmrc", ".node-version",
              "index.html", "BPP_RESEARCH_CONSOLE_MASTER_PROMPT_20261006.txt"}
ROOT_PATTERNS = ("tsconfig*.json", "vite.config.*", "vitest.config.*", "playwright.config.*",
                 "postcss.config.*", "tailwind.config.*", "eslint.config.*", "next.config.*")
IGNORED_PARTS = {"node_modules", ".venv", "__pycache__", ".git", ".cache", "test-results",
                 "playwright-report", "research", "dist", "delivery", "backups"}
EVIDENCE_SUFFIXES = {".json", ".md", ".txt", ".log", ".png", ".jpg", ".jpeg", ".webp", ".csv", ".html"}
REQUIRED_FILES = {"README.md", "package.json", "package-lock.json", "requirements.lock",
                  "scripts/setup.sh", "scripts/console.sh", "scripts/import_data.py",
                  "scripts/convert_data.py", "scripts/validate_data.py", "scripts/clean_rebuild.py",
                  "tools/browser/package.json", "tools/browser/package-lock.json", "core/replay.mjs",
                  "docs/MIGRATION.md"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def allowed(relative: Path, is_directory: bool = False) -> bool:
    parts = relative.parts
    if any(part in IGNORED_PARTS or part.startswith(".env") for part in parts):
        return False
    if relative.suffix in {".pyc", ".pyo"} or relative.name.endswith((".tmp", ".bak")):
        return False
    if len(parts) == 1:
        return relative.name in ROOT_FILES or any(fnmatch.fnmatch(relative.name, p) for p in ROOT_PATTERNS)
    if parts[0] == "inputs":
        return len(parts) == 2 and relative.suffix.lower() == ".zip"
    if parts[0] == "artifacts":
        return is_directory or relative.suffix.lower() in EVIDENCE_SUFFIXES
    if parts[0] == "tools":
        return parts == ("tools", "browser") and is_directory or (
            len(parts) == 3 and parts[:2] == ("tools", "browser")
            and (parts[2] in {"package.json", "package-lock.json"} or relative.suffix == ".mjs"))
    if parts[:2] == ("public", "data"):
        return False
    return parts[0] in SOURCE_DIRS


def collect_files(root: Path) -> list[Path]:
    # Restrict traversal too: avoid walking .venv/node_modules/research merely to exclude them.
    selected = []
    for child in sorted(root.iterdir()):
        # The workspace keeps one physical input directory. Materialize only
        # that known link in a portable delivery; other source links stay invalid.
        workspace_inputs = root.parent.parent / "data" / "bpp" / "inputs"
        shared_input = (child.name == "inputs" and root.name == "frontend"
                        and root.parent.name == "src" and workspace_inputs.is_dir()
                        and child.resolve() == workspace_inputs.resolve())
        if child.is_symlink() and not shared_input:
            if allowed(child.relative_to(root)) or child.name in SOURCE_DIRS | {"inputs", "artifacts", "tools"}:
                raise ValueError(f"Delivery source must not be a symlink: {child}")
            continue
        if child.is_file() and allowed(child.relative_to(root)):
            selected.append(child)
        elif child.is_dir() and child.name in SOURCE_DIRS | {"inputs", "artifacts", "tools"}:
            pending = [child]
            while pending:
                directory = pending.pop()
                for path in sorted(directory.iterdir()):
                    relative = path.relative_to(root)
                    if not allowed(relative, is_directory=path.is_dir()):
                        continue
                    if path.is_symlink():
                        raise ValueError(f"Delivery source must not be a symlink: {relative}")
                    if path.is_dir():
                        pending.append(path)
                    elif path.is_file():
                        selected.append(path)
    return sorted(selected, key=lambda path: path.relative_to(root).as_posix())


def write_entry(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    entry = zipfile.ZipInfo("bpp-research-console/" + name, date_time=(2026, 10, 6, 0, 0, 0))
    entry.create_system = 3
    mode = 0o755 if name.endswith(".sh") else 0o644
    entry.external_attr = (stat.S_IFREG | mode) << 16
    entry.compress_type = zipfile.ZIP_STORED if name.endswith((".zip", ".png", ".jpg", ".webp")) else zipfile.ZIP_DEFLATED
    archive.writestr(entry, content)


def package(root: Path, destination: Path) -> dict:
    root = root.resolve()
    paths = collect_files(root)
    names = {path.relative_to(root).as_posix() for path in paths}
    missing = REQUIRED_FILES - names
    if missing:
        raise ValueError("Required delivery files are missing: " + ", ".join(sorted(missing)))
    inputs = [path for path in paths if path.relative_to(root).parts[0] == "inputs"]
    if len(inputs) != 1 or sha256(inputs[0].read_bytes()) != EXPECTED_INPUT_SHA256:
        raise ValueError("Exactly one original input ZIP with the expected SHA256 is required")
    if not any(name.startswith("tests/replay") and name.endswith(".mjs") for name in names):
        raise ValueError("Replay tests are required in the delivery")
    destination = destination.resolve()
    if destination in paths:
        raise ValueError("Delivery output must not overwrite a source file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "original_input_included": True, "original_input_sha256": EXPECTED_INPUT_SHA256,
                "generated_data_included": False,
                "rebuild_command": "bash scripts/console.sh setup && bash scripts/console.sh data-convert",
                "files": {}}
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths:
                name = path.relative_to(root).as_posix()
                data = path.read_bytes()
                manifest["files"][name] = {"bytes": len(data), "sha256": sha256(data)}
                write_entry(archive, name, data)
            write_entry(archive, "DELIVERY_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        # Read every member back before publishing the package; detect corruption and omissions.
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Delivery ZIP failed CRC verification")
            for name, entry in manifest["files"].items():
                data = archive.read("bpp-research-console/" + name)
                if len(data) != entry["bytes"] or sha256(data) != entry["sha256"]:
                    raise ValueError(f"Delivery member failed hash verification: {name}")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = sha256(destination.read_bytes())
    checksum = destination.with_suffix(destination.suffix + ".sha256")
    checksum.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    return {"status": "PASS", "path": str(destination), "bytes": destination.stat().st_size,
            "sha256": digest, "checksum_path": str(checksum), "source_files": len(paths),
            "original_input_included": True, "generated_data_included": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "delivery/bpp-research-console-delivery.zip")
    parser.add_argument("--list", action="store_true", help="List current allowlisted files without packaging")
    args = parser.parse_args()
    if args.list:
        for file in collect_files(args.root.resolve()):
            print(file.relative_to(args.root.resolve()).as_posix())
    else:
        print(json.dumps(package(args.root, args.output), ensure_ascii=False, indent=2))
