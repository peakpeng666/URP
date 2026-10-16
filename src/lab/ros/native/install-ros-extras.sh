#!/usr/bin/env bash
# Installs extra ROS 2 Humble packages without sudo: the official .deb files are fetched with
# `apt download` (signature-checked by apt) and unpacked into a project-local prefix that the
# simulation session puts on AMENT_PREFIX_PATH / LD_LIBRARY_PATH. /opt/ros is never touched.
#
#   foxglove_bridge      WebSocket bridge that streams ROS topics to the workbench's 3D and telemetry views
#   rosx_introspection   runtime dependency of foxglove_bridge
set -euo pipefail
root="$(cd "$(dirname "$0")/../../../.." && pwd)"
dest="$root/setup/2026-10-15/deployment/runtime/ros-extras"
packages=(ros-humble-foxglove-bridge ros-humble-rosx-introspection)

mkdir -p "$dest/debs" "$dest/root"
cd "$dest/debs"
missing=()
for p in "${packages[@]}"; do
  ls "${p}"_*.deb >/dev/null 2>&1 || missing+=("$p")
done
if ((${#missing[@]})); then
  apt download "${missing[@]}"
fi
for deb in "$dest"/debs/*.deb; do
  dpkg-deb -x "$deb" "$dest/root"
done
sha256sum "$dest"/debs/*.deb > "$dest/manifest.sha256"

prefix="$dest/root/opt/ros/humble"
bin="$prefix/lib/foxglove_bridge/foxglove_bridge"
[[ -x "$bin" ]] || { echo "foxglove_bridge 不在预期位置：$bin" >&2; exit 1; }
# A quick load test: every shared library must resolve against the system ROS plus this prefix.
set +u
source /opt/ros/humble/setup.bash
set -u
if LD_LIBRARY_PATH="$prefix/lib:${LD_LIBRARY_PATH:-}" ldd "$bin" | grep -q "not found"; then
  LD_LIBRARY_PATH="$prefix/lib:${LD_LIBRARY_PATH:-}" ldd "$bin" | grep "not found" >&2
  exit 1
fi
echo "ROS 扩展已就绪：$prefix"
