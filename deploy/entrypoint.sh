#!/bin/bash
# Container start: multicast route for Gazebo discovery when the kernel allows it,
# then the workbench as uid 1000. Failure to add the route does not stop the bench.
set -euo pipefail
mkdir -p /data/lab /data/archive
chown -R urp:urp /data
if command -v ip >/dev/null 2>&1; then
  ip link set lo multicast on 2>/dev/null || true
  ip route replace 239.255.0.0/16 dev lo 2>/dev/null || true
fi
cd /opt/urp/src/lab
if [[ "$(id -u)" -eq 0 ]]; then
  exec setpriv --reuid=urp --regid=urp --init-groups -- "$@"
fi
exec "$@"
