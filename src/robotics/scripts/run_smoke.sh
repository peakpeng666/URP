#!/usr/bin/env bash
# Deliberately no installation, download, credentials, benchmark input, or hardware route.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/evidence/runtime_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
fail() { printf '%s\n' "$1" >&2; printf '{"runtime_executed":false,"success":false,"stage":"preflight","reason":"%s"}\n' "$1" > "$OUT/preflight.json"; exit 2; }
[[ -r /opt/ros/humble/setup.bash ]] || fail 'ROS 2 Humble is not installed; runtime NOT executed'
# ROS setup may inspect unset variables.
set +u
source /opt/ros/humble/setup.bash
set -u
[[ "${ROS_DISTRO:-}" == humble ]] || fail 'Only ROS 2 Humble is supported'
for exe in ros2 ign timeout setsid; do command -v "$exe" >/dev/null || fail "Missing required executable: $exe"; done
ign gazebo --versions > "$OUT/gazebo_versions.txt" 2>&1 || fail 'Cannot inspect Gazebo versions'
grep -Eq '(^|[^0-9])6\.[0-9]+' "$OUT/gazebo_versions.txt" || fail 'Gazebo Fortress major version 6 required'
ros2 pkg prefix urp_route_sim >/dev/null 2>&1 || fail 'Build and source the urp_route_sim colcon workspace first'
ros2 pkg prefix ros_gz_bridge >/dev/null 2>&1 || fail 'ros_gz_bridge is missing'
# Both DDS and Gazebo transport restricted to this host; dedicated simulator namespace.
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=71 IGN_IP=127.0.0.1
export IGN_PARTITION="urp_synthetic_$(date +%s)_$$"
export URP_ALLOW_SYNTHETIC_COMMANDS=1
printf '{"runtime_executed":false,"success":true,"stage":"preflight","stack":"Humble/Fortress"}\n' > "$OUT/preflight.json"
LAUNCH_PID=''
cleanup() {
  if [[ -n "$LAUNCH_PID" ]]; then
    kill -INT -- "-$LAUNCH_PID" 2>/dev/null || true
    for _ in {1..50}; do kill -0 "$LAUNCH_PID" 2>/dev/null || break; sleep .1; done
    kill -TERM -- "-$LAUNCH_PID" 2>/dev/null || true
    sleep .5
    kill -KILL -- "-$LAUNCH_PID" 2>/dev/null || true
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM
setsid ros2 launch urp_route_sim synthetic_fortress.launch.py rviz:=false > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
set +e
timeout --signal=INT --kill-after=5s 90s ros2 run urp_route_sim synthetic_smoke --output-dir "$OUT" --timeout 65 > "$OUT/controller.log" 2>&1
RESULT=$?
set -e
if [[ ! -f "$OUT/smoke_result.json" ]]; then
  printf '{"runtime_executed":true,"success":false,"reason":"controller exited without final report; inspect logs"}\n' > "$OUT/smoke_result.json"
fi
printf 'Report: %s/smoke_result.json\n' "$OUT"
exit "$RESULT"
