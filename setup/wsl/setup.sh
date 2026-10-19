#!/usr/bin/env bash
# Fresh Ubuntu (including WSL2) preparation for the workbench. Does not install ROS.
# ROS 2 Humble and Gazebo Fortress stay on the system image or the simulation container;
# this script only builds the pinned Python and Node environments.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
# shellcheck source=env.sh
source "$root/setup/wsl/env.sh"

if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y curl ca-certificates xz-utils tar
fi

if ! command -v uv >/dev/null 2>&1 || [[ "$(uv --version 2>/dev/null || true)" != *'0.12.23'* ]]; then
  curl -LsSf https://astral.sh/uv/0.12.23/install.sh | sh
  # shellcheck source=env.sh
  source "$root/setup/wsl/env.sh"
fi

node_prefix="${HOME}/.local/node-v24.22.0"
if ! command -v node >/dev/null 2>&1 || [[ "$(node --version)" != v24.22.0 ]]; then
  archive="$(mktemp)"
  curl -fsSL "https://nodejs.org/dist/v24.22.0/node-v24.22.0-linux-x64.tar.gz" -o "$archive"
  echo "28ea0a438de9a13bd7891fd758eee6c7819ee8af5442dfd8d45bd65e56d4228c  ${archive}" | sha256sum -c -
  mkdir -p "$node_prefix"
  tar -xzf "$archive" -C "$node_prefix" --strip-components=1
  rm -f "$archive"
  hash -r
fi

uv python install 3.12.13
uv sync --locked --extra solvers --python 3.12.13
(cd src/lab && uv sync --locked --inexact --python 3.12.13)
if [[ -f src/lab/vendor/wheels/fields2cover-2.1.0-cp312-cp312-linux_x86_64.whl ]]; then
  src/lab/.venv/bin/python - <<'PY'
import hashlib, json, pathlib, subprocess
lab = pathlib.Path('src/lab')
manifest = json.loads((lab / 'vendor/fields2cover-manifest.json').read_text())
wheel = lab / manifest['wheel']
if hashlib.sha256(wheel.read_bytes()).hexdigest() != manifest['wheel_sha256']:
    raise SystemExit('Fields2Cover wheel 指纹不匹配，拒绝安装')
subprocess.run(['uv', 'pip', 'install', '--no-deps', '--python', str(lab / '.venv/bin/python'), str(wheel)], check=True)
PY
fi
(cd src/frontend && npm ci --engine-strict --no-audit --no-fund && npm run build)
printf '工作台依赖已按锁文件装好。启动：bash setup/wsl/run-lab.sh\n'
printf '仿真需要另外安装 ROS 2 Humble 与 Gazebo Fortress，见 DEPLOY.md。\n'
