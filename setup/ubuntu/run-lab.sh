#!/usr/bin/env bash
# Start the workbench. WSL2 binds all interfaces so the Windows browser can use
# localhost forwarding. Native Ubuntu keeps the laptop default, 127.0.0.1.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
# shellcheck source=env.sh
source "$root/setup/ubuntu/env.sh"
if [[ ! -x src/lab/.venv/bin/python || ! -f src/frontend/dist/index.html ]]; then
  bash setup/ubuntu/setup.sh
fi
wsl=0
if [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null; then
  wsl=1
fi
if [[ -f src/lab/runtime/native/bridge/profile.json ]]; then
  export URP_SIM_PROFILE=image
fi
if [[ "$wsl" -eq 1 ]]; then
  export URP_BIND_HOST=0.0.0.0
  export URP_FOXGLOVE_BIND=0.0.0.0
  export URP_BROWSER_HOST=127.0.0.1
  export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
else
  export URP_BIND_HOST="${URP_BIND_HOST:-127.0.0.1}"
  export URP_FOXGLOVE_BIND="${URP_FOXGLOVE_BIND:-127.0.0.1}"
  export URP_BROWSER_HOST="${URP_BROWSER_HOST:-127.0.0.1}"
fi
exec bash setup/run.sh lab "$@"
