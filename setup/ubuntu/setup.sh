#!/usr/bin/env bash
# Ubuntu 22.04 setup for WSL2 and for a native machine. Installs the pinned
# Python/Node workbench and ROS 2 Humble + Gazebo Fortress.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
# shellcheck source=env.sh
source "$root/setup/ubuntu/env.sh"

wsl=0
if [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null; then
  wsl=1
fi

if [[ ! -r /etc/os-release ]]; then
  echo '需要 Ubuntu 22.04。没有 /etc/os-release。' >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
  echo "ROS 2 Humble 需要 Ubuntu 22.04。当前是 ${PRETTY_NAME:-unknown}。" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v gpg >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y curl ca-certificates gnupg
fi

if [[ ! -f /usr/share/keyrings/ros-archive-keyring.gpg ]]; then
  sudo curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
fi
if [[ ! -f /etc/apt/sources.list.d/ros2.list ]]; then
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
fi

sudo apt-get update
mapfile -t packages < <(grep -vE '^[[:space:]]*(#|$)' "$root/deploy/ros-packages.txt")
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"

if ! command -v uv >/dev/null 2>&1 || [[ "$(uv --version 2>/dev/null || true)" != *'0.12.23'* ]]; then
  curl -LsSf https://astral.sh/uv/0.12.23/install.sh | sh
  # shellcheck source=env.sh
  source "$root/setup/ubuntu/env.sh"
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

bash src/lab/ros/native/install-ros-extras.sh
python3 deploy/record-sim-profiles.py

if [[ "$wsl" -eq 1 ]]; then
  cat <<'EOF'
这是 WSL2。Windows 浏览器通过 localhost 转发访问 http://localhost:4100/ 。
Gazebo 默认软件渲染。若 `nvidia-smi` 在 WSL 里可用，启动前可以 export LIBGL_ALWAYS_SOFTWARE=0。
内存限制见 setup/ubuntu/wslconfig.example，改完后在 PowerShell 执行 wsl --shutdown。
启动：bash setup/ubuntu/run-lab.sh
EOF
else
  cat <<'EOF'
这是原生 Ubuntu 22.04。网关只监听 127.0.0.1。有 NVIDIA 驱动时直接用 GPU，不强制软件渲染。
没有可用 GPU 时启动前 export LIBGL_ALWAYS_SOFTWARE=1。
启动：bash setup/ubuntu/run-lab.sh
EOF
fi
