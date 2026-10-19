#!/bin/bash
# Container start. DDS discovery is unicast on lo (setup/cyclonedds.xml);
# this script does not add a multicast route.
set -euo pipefail
mkdir -p /data/lab /data/archive /data/lab/matplotlib /home/urp
chown -R urp:urp /data /home/urp
cd /opt/urp/src/lab
if [[ "$(id -u)" -eq 0 ]]; then
  # setpriv keeps the root environment, including HOME=/root, which matplotlib cannot write.
  export HOME=/home/urp
  export MPLCONFIGDIR=/data/lab/matplotlib
  exec setpriv --reuid=urp --regid=urp --init-groups -- "$@"
fi
exec "$@"
