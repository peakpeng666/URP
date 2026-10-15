#!/usr/bin/env bash
# Builds the project-local parameter_bridge exit guard and records the fingerprints it was validated against.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
out="$here/../../runtime/native"
mkdir -p "$out"
gcc -O2 -Wall -Wextra -shared -fPIC -o "$out/liburp_bridge_exit_guard.so" "$here/bridge_exit_guard.c" -ldl
/usr/bin/python3 - "$here" "$out" <<'PY'
import hashlib, json, sys
from pathlib import Path
here, out = Path(sys.argv[1]), Path(sys.argv[2])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest = {
    'library': str(out / 'liburp_bridge_exit_guard.so'),
    'library_sha256': sha(out / 'liburp_bridge_exit_guard.so'),
    'source_sha256': sha(here / 'bridge_exit_guard.c'),
    'validated_against': {p: sha(p) for p in (
        '/opt/ros/humble/lib/ros_gz_bridge/parameter_bridge',
        '/opt/ros/humble/lib/libros_gz_bridge.so',
        '/lib/x86_64-linux-gnu/libc.so.6',
        '/usr/lib/x86_64-linux-gnu/libignition-transport11.so.11')},
    'evidence': 'setup/2026-10-15/integration/bridge-exit/',
}
(out / 'bridge-exit-guard-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
PY
