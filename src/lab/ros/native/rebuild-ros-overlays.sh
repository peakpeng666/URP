#!/usr/bin/env bash
# Rebuilds the two fingerprint-checked ROS overlays (TF2 registration gate, GUI plugin lifetime) exactly as validated.
# The commands reproduce the recorded binaries byte for byte; tf_overlay.py still refuses anything that differs.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd -P)"
dep="setup/2026-10-15/deployment"
cd "$root"
mkdir -p "$dep/runtime"
if [[ ! -f "$dep/runtime/tf-repro/liburp_tf_buffer.so" ]]; then
  set +u; source /opt/ros/humble/setup.bash; set -u
  cmake -S "$dep/tf-repro" -B "$dep/runtime/tf-repro" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo >/dev/null
  cmake --build "$dep/runtime/tf-repro" --target urp_tf_buffer >/dev/null
fi
if [[ ! -f "$dep/runtime/liburp_gui_lifetime.so" ]]; then
  g++ -O2 -g -std=c++17 -shared -fPIC -o "$root/$dep/runtime/liburp_gui_lifetime.so" "$dep/gui-plugin-lifetime.cpp" -ldl
fi
/usr/bin/python3 -c "import sys; sys.path.insert(0, '$dep'); import tf_overlay as t; t.verified_candidate(); t.verified_gui_lifetime(); print('ROS overlays verified')"
