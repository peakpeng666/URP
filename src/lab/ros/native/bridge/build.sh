#!/usr/bin/env bash
# Source-level parameter_bridge fix; no installed package or Python is modified.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
out="$here/../../../runtime/native/bridge"
set +u
source /opt/ros/humble/setup.bash
set -u
cmake -S "$here" -B "$out" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$out" -j 2
