#!/usr/bin/python3
"""Read-only guard for this setup's exact apt transaction."""
import json
import pathlib
import shutil
import sys

import apt
import apt_pkg

base = pathlib.Path(__file__).resolve().parent
apt_pkg.init_config()
apt_pkg.config.set("APT::Install-Recommends", "false")
apt_pkg.config.set("Dir::Etc::sourcelist", "/etc/apt/sources.list")
apt_pkg.config.set("Dir::Etc::sourceparts", str(base / "apt-sources"))
cache = apt.Cache()
for spec in (base / "apt-requested-versions.txt").read_text().splitlines():
    name, version = spec.split("=", 1)
    if version not in cache[name].versions:
        sys.exit(f"STOP: locked version unavailable: {spec}")
    cache[name].candidate = cache[name].versions[version]
    cache[name].mark_install(auto_fix=True, from_user=True)
expected = {p["name"]: p["version"] for p in json.loads((base / "apt-plan.json").read_text())["packages"]}
sites = {"cn.archive.ubuntu.com", "security.ubuntu.com", "packages.ros.org"}
for pkg in cache.get_changes():
    version = pkg.candidate
    if pkg.marked_delete or pkg.installed is not None:
        sys.exit(f"STOP: removal/replacement of existing package: {pkg.name}")
    if expected.get(pkg.name) != version.version:
        sys.exit(f"STOP: transaction differs from reviewed plan: {pkg.name}={version.version}")
    if not version.origins or not all(o.trusted and o.site in sites for o in version.origins):
        sys.exit(f"STOP: unexpected or untrusted origin: {pkg.name}")
if cache.broken_count:
    sys.exit("STOP: broken dependency resolution")
needed = cache.required_download + cache.required_space + 1024**3
if shutil.disk_usage("/").free < needed:
    sys.exit("STOP: insufficient free space including 1 GiB margin")
print(f"APT guard passed: {len(cache.get_changes())} new, 0 upgrades, 0 removals; "
      f"download {cache.required_download:,} bytes, installed {cache.required_space:,} bytes.")
