#!/usr/bin/env bash
# Bind all interfaces inside WSL so the Windows browser can open http://localhost:4100.
# Shutdown stays on loopback: use bash setup/run.sh lab-stop from inside WSL.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
# shellcheck source=env.sh
source "$root/setup/wsl/env.sh"
if [[ ! -x src/lab/.venv/bin/python || ! -f src/frontend/dist/index.html ]]; then
  bash setup/wsl/setup.sh
fi
export URP_BIND_HOST=0.0.0.0
export URP_FOXGLOVE_BIND=0.0.0.0
export URP_BROWSER_HOST=127.0.0.1
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
exec bash setup/run.sh lab "$@"
