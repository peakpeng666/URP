#!/usr/bin/env bash
# Minimal deployment acceptance, not a formal CVRP batch or physical Gazebo test.
set -euo pipefail
image="${1:?image}"
revision="${2:?expected full revision}"
kind="${3:?bench or sim}"
output="${4:?new evidence directory}"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected full commit SHA' >&2; exit 2; }
[[ "$kind" == bench || "$kind" == sim ]] || { echo 'Expected bench or sim' >&2; exit 2; }
mkdir -p "$(dirname "$output")"
mkdir "$output"
output="$(cd "$output" && pwd)"
container="urp-image-check-${kind}-$$"
cleanup() {
  local status=$?
  trap - EXIT
  docker logs "$container" >"$output/container.log" 2>&1 || true
  docker inspect "$container" >"$output/container.json" 2>&1 || true
  if [[ ! -d "$output/cohort" ]]; then
    docker cp "$container:/tmp/urp-cohort-smoke" "$output/cohort" >/dev/null 2>&1 || true
  fi
  docker rm -f "$container" >/dev/null 2>&1 || true
  printf '%s\n' "$status" >"$output/exit-code.txt"
  exit "$status"
}
trap cleanup EXIT
docker image inspect "$image" >"$output/image.json"
actual="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image")"
[[ "$actual" == "$revision" ]] || { echo "Image revision mismatch: $actual" >&2; exit 1; }
docker run -d --name "$container" -p 127.0.0.1::4100 "$image" >"$output/container-id.txt"
port="$(docker port "$container" 4100/tcp | sed -n 's/^127\.0\.0\.1://p')"
[[ "$port" =~ ^[0-9]+$ ]] || { echo 'Cannot determine published port' >&2; exit 1; }
base="http://127.0.0.1:${port}"

wait_healthy() {
  local status
  for _ in $(seq 1 100); do
    status="$(docker inspect --format '{{.State.Status}} {{.State.Health.Status}}' "$container")"
    [[ "$status" != exited* && "$status" != dead* ]] || { echo "$status" >&2; return 1; }
    if [[ "$status" == 'running healthy' ]]; then return 0; fi
    sleep 2
  done
  echo "Container did not become healthy: $status" >&2
  return 1
}
wait_healthy
curl --fail --silent --show-error --max-time 10 "$base/lab/api/health" >"$output/health.json"
python3 - "$output/health.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    assert json.load(stream)['status'] == 'ok'
PY
curl --fail --silent --show-error --max-time 10 "$base/api/health" >"$output/archive-health.json"
python3 - "$output/archive-health.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    assert json.load(stream)['status'] == 'ok'
PY
curl --fail --silent --show-error --max-time 10 "$base/" >"$output/index.html"
test -s "$output/index.html"
code="$(curl --silent --show-error --max-time 10 -o "$output/shutdown.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' -d '{}' "$base/lab/api/shutdown")"
[[ "$code" == 403 ]]
grep -q shutdown_forbidden "$output/shutdown.json"
docker exec "$container" sh -c 'test "$(cat /opt/urp/REVISION)" = "$URP_REVISION"'
actual="$(docker exec "$container" cat /opt/urp/REVISION)"
[[ "$actual" == "$revision" ]]
docker exec --user urp "$container" /opt/urp/.venv/bin/python \
  -c 'from pyvrp import Model; from ortools.constraint_solver import pywrapcp; Model(); pywrapcp.Solver("image-check")' \
  >"$output/root-native-solvers.log" 2>&1
docker exec --user urp "$container" /opt/urp/src/lab/.venv/bin/python \
  -c 'from ompl import base as ob, geometric as og; space=ob.RealVectorStateSpace(2); planner=og.SimpleSetup(space)' \
  >"$output/motion-planning.log" 2>&1
docker exec --user urp "$container" /opt/urp/.venv/bin/python \
  /opt/urp/deploy/check-cohort.py --output /tmp/urp-cohort-smoke >"$output/cohort.log" 2>&1
docker cp "$container:/tmp/urp-cohort-smoke" "$output/cohort"
test -s "$output/cohort/summary.json"
if [[ "$kind" == sim ]]; then
  # Loadability only. Real Gazebo/ROS session acceptance remains a separate gate.
  docker exec --user urp "$container" /opt/urp/src/lab/.venv/bin/python \
    /opt/urp/deploy/check-fields2cover.py >"$output/fields2cover.log" 2>&1
  docker exec --user urp "$container" bash -c \
    'source /opt/ros/humble/setup.bash && ros2 pkg prefix ros_gz_bridge && ign gazebo --versions' \
    >"$output/simulation-tools.log" 2>&1
fi
docker restart "$container" >"$output/restart.txt"
wait_healthy
curl --fail --silent --show-error --max-time 10 "$base/lab/api/health" >"$output/health-after-restart.json"
python3 - "$output/health-after-restart.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    assert json.load(stream)['status'] == 'ok'
PY
printf 'PASS: %s revision %s (deployment smoke, not a formal experiment)\n' "$kind" "$revision" | tee "$output/summary.txt"
