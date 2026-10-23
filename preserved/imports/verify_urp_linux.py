#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify the URP migration package on this Linux box.

Re-hashes every entry in sha256_local_baseline.jsonl against the local tree,
reports missing / size-mismatch / hash-mismatch, and lists local files that the
baseline does not cover. Also checks the two handoff artifacts against the
delivery receipt.
"""
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

BASE = "/home/peakpeng/Desktop/URP_云盘全量迁移_20261009"
HAND = os.path.join(BASE, "_交接包")
BASELINE = os.path.join(HAND, "sha256_local_baseline.jsonl")
ROOTS = ("URP_primary", "URP_secondary", "BPP")

ARTIFACTS = {
    "URP云盘终点冻结交接_完整清单与审计_20261009.zip":
        "4e1b8a4e0e2c8a2c0d5e9a85141697a306e1b69be2653e4a15c540815a7ee33f",
    "URP云盘终点冻结交接总说明_20261009.txt":
        "dfec715e1287c32909b04c5105caeba9f242b2a1b330d6cd040f85e43081ce1d",
}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(entry):
    rel, size, want = entry
    p = os.path.join(BASE, rel)
    if not os.path.isfile(p):
        return ("missing", rel, None, None)
    try:
        actual_size = os.path.getsize(p)
    except OSError as exc:
        return ("stat_error", rel, str(exc), None)
    if actual_size != size:
        return ("size_mismatch", rel, f"{actual_size} != {size}", None)
    try:
        got = sha256_of(p)
    except OSError as exc:
        return ("read_error", rel, str(exc), None)
    if got != want:
        return ("hash_mismatch", rel, got, want)
    return ("ok", rel, None, None)


def main():
    entries = []
    with open(BASELINE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rel = r["path"].replace("\\", "/")
            entries.append((rel, r["size"], r["sha256"].lower()))
    print(f"baseline entries: {len(entries)}", flush=True)

    tally = {}
    problems = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for i, res in enumerate(pool.map(check, entries, chunksize=64), 1):
            tally[res[0]] = tally.get(res[0], 0) + 1
            if res[0] != "ok":
                problems.append(res)
            if i % 8000 == 0:
                print(f"  ...{i}/{len(entries)}", flush=True)

    print("\n=== hash verification ===")
    for k, v in sorted(tally.items()):
        print(f"  {k:16s} {v}")
    if problems:
        print("\n--- first 25 problems ---")
        for kind, rel, a, b in problems[:25]:
            print(f"  {kind:14s} {rel}  {a or ''}")

    # files present locally but absent from the baseline
    covered = {rel for rel, _, _ in entries}
    extras = []
    for root in ROOTS:
        for dirpath, _dirs, files in os.walk(os.path.join(BASE, root)):
            for name in files:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, BASE)
                if rel not in covered:
                    extras.append(rel)
    print(f"\n=== files under {ROOTS} not in baseline: {len(extras)} ===")
    for rel in extras[:25]:
        print("  ", rel)

    total_bytes = sum(
        os.path.getsize(os.path.join(BASE, rel))
        for rel, _, _ in entries
        if os.path.isfile(os.path.join(BASE, rel))
    )
    print(f"\nverified bytes on disk: {total_bytes:,}")

    print("\n=== handoff artifacts vs receipt ===")
    for name, want in ARTIFACTS.items():
        p = os.path.join(HAND, name)
        if not os.path.isfile(p):
            print(f"  MISSING  {name}")
            continue
        got = sha256_of(p)
        print(f"  {'MATCH ' if got == want else 'DIFFER'} {name}")
        if got != want:
            print(f"         got  {got}\n         want {want}")
    return 0 if tally.get("ok") == len(entries) and not extras else 1


if __name__ == "__main__":
    sys.exit(main())
