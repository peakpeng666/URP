#!/usr/bin/env bash
# Public one-command install for the URP workbench and Gazebo stack.
#   curl -fsSL https://raw.githubusercontent.com/peakpeng666/URP/deploy/install.sh | bash
# No GitHub login and no docker login. Docker pulls ghcr.io/peakpeng666/urp-sim
# and does not clone the repository. Ubuntu 22.04 without Docker uses a shallow
# sparse clone. See DEPLOY.md.
set -euo pipefail

REPO=https://github.com/peakpeng666/URP.git
RAW="${URP_RAW:-https://raw.githubusercontent.com/peakpeng666/URP/deploy}"
BRANCH=deploy
TAG="${URP_IMAGE_TAG:-deploy}"
SIM_IMAGE="ghcr.io/peakpeng666/urp-sim:${TAG}"
STATE="${URP_HOME:-${HOME}/.local/share/urp}"
BIN="${HOME}/.local/bin/urp"
PORT="${URP_PORT:-4100}"
HEALTH="http://127.0.0.1:${PORT}/lab/api/health"
PAGE="http://localhost:${PORT}/"

export GIT_TERMINAL_PROMPT=0
export DOCKER_CLI_HINTS=false

cmd="${1:-up}"

say() { printf '%s\n' "$*"; }
die() { printf '%s\n' "$*" >&2; exit 1; }

visibility_help() {
  cat >&2 <<'EOF'
匿名拉取 ghcr.io/peakpeng666/urp-sim 失败。不要执行 docker login，也不要申请令牌。
GitHub 用 Actions 的 GITHUB_TOKEN 推上去的包默认仍是私有，工作流改不了这个开关。
主人在浏览器里做一次：
  https://github.com/users/peakpeng666/packages/container/urp-sim/settings
  Package settings → Change package visibility → Public
  对 urp-bench 重复一次。
若页面写着未关联仓库：Connect repository → peakpeng666/URP。
镜像标签 org.opencontainers.image.source=https://github.com/peakpeng666/URP 会在推送时写入。
EOF
}

have_docker() {
  command -v docker >/dev/null 2>&1 || return 1
  docker info >/dev/null 2>&1
}

ubuntu_2204() {
  [[ -r /etc/os-release ]] || return 1
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "22.04" ]]
}

install_cli() {
  mkdir -p "$(dirname "$BIN")" "$STATE/deploy"
  if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" && "${BASH_SOURCE[0]}" != "$BIN" ]]; then
    cp "${BASH_SOURCE[0]}" "$BIN"
  else
    curl -fsSL "${RAW}/install.sh" -o "$BIN"
  fi
  chmod 755 "$BIN"
}

fetch_compose() {
  mkdir -p "$STATE/deploy"
  curl -fsSL "${RAW}/deploy/docker-compose.sim.yml" -o "$STATE/deploy/docker-compose.sim.yml"
  curl -fsSL "${RAW}/deploy/docker-compose.gpu.yml" -o "$STATE/deploy/docker-compose.gpu.yml"
  curl -fsSL "${RAW}/deploy/docker-compose.display.yml" -o "$STATE/deploy/docker-compose.display.yml"
  curl -fsSL "${RAW}/deploy/docker-compose.fuel.yml" -o "$STATE/deploy/docker-compose.fuel.yml"
  curl -fsSL "${RAW}/deploy/fetch-fuel.sh" -o "$STATE/deploy/fetch-fuel.sh"
  chmod 755 "$STATE/deploy/fetch-fuel.sh"
}

compose() {
  docker compose -f "$STATE/deploy/docker-compose.sim.yml" "$@"
}

compose_files() {
  local -a files=(-f "$STATE/deploy/docker-compose.sim.yml")
  if [[ "${URP_GPU:-0}" == "1" && -f "$STATE/deploy/docker-compose.gpu.yml" ]]; then
    files+=(-f "$STATE/deploy/docker-compose.gpu.yml")
  fi
  if [[ "${URP_DISPLAY:-0}" == "1" && -f "$STATE/deploy/docker-compose.display.yml" ]]; then
    files+=(-f "$STATE/deploy/docker-compose.display.yml")
    export DISPLAY="${DISPLAY:-:0}"
  fi
  if [[ -d "${URP_FUEL_DIR:-$STATE/fuel}/fuel.gazebosim.org" ]]; then
    files+=(-f "$STATE/deploy/docker-compose.fuel.yml")
    export URP_FUEL_DIR="${URP_FUEL_DIR:-$STATE/fuel}"
  fi
  docker compose "${files[@]}" "$@"
}

pull_sim() {
  if docker pull "$SIM_IMAGE" </dev/null; then
    return 0
  fi
  if docker image inspect "$SIM_IMAGE" >/dev/null 2>&1; then
    say "注册表暂时拉不到，使用本机已有的 ${SIM_IMAGE}。"
    return 0
  fi
  visibility_help
  return 1
}

wait_health() {
  local i
  for i in $(seq 1 90); do
    if curl -fsS "$HEALTH" 2>/dev/null | grep -q '"status":"ok"'; then
      return 0
    fi
    sleep 2
  done
  say "健康检查还没有返回 ${HEALTH}" >&2
  compose logs --tail 60 >&2 || true
  return 1
}

open_page() {
  say "$PAGE"
  if [[ -n "${WSL_DISTRO_NAME:-}" ]] && command -v wslview >/dev/null 2>&1; then
    wslview "$PAGE" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$PAGE" >/dev/null 2>&1 || true
  fi
}

docker_up() {
  install_cli
  fetch_compose
  pull_sim
  compose_files up -d --no-build --pull never --remove-orphans
  wait_health
  open_page
  say "已在后台运行。停止：urp down    状态：urp status    更新：urp update"
  say "若 shell 找不到 urp，把 ~/.local/bin 加入 PATH。"
}

clone_src() {
  local src="$STATE/src"
  if ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y git ca-certificates curl
  fi
  if [[ ! -d "$src/.git" ]]; then
    git clone --depth 1 --filter=blob:none --sparse --branch "$BRANCH" "$REPO" "$src" >&2
    git -C "$src" sparse-checkout set --no-cone \
      '/*' \
      '!/src/repos/' \
      '!/data/bpp/' \
      '!/data/cifar-training/' \
      '!/experiments/' \
      '!/papers/' \
      '!/literature/' \
      '!/materials/' >&2
  fi
  printf '%s\n' "$src"
}

update_src() {
  local src="$1"
  git -C "$src" fetch --depth 1 origin "$BRANCH"
  git -C "$src" checkout --detach --quiet "origin/${BRANCH}"
}

native_up() {
  install_cli
  local src
  src="$(clone_src)"
  if [[ "${URP_UPDATE:-0}" == "1" ]]; then
    update_src "$src"
    bash "$src/setup/ubuntu/setup.sh"
  fi
  say "$PAGE"
  if curl -fsS "$HEALTH" >/dev/null 2>&1; then
    bash "$src/setup/run.sh" lab-stop || true
  fi
  # Foreground so this terminal owns the process. The URL is printed above.
  exec bash "$src/setup/ubuntu/run-lab.sh"
}

route() {
  case "$cmd" in
    up|update)
      [[ "$cmd" == update ]] && export URP_UPDATE=1
      if have_docker; then
        docker_up
      elif ubuntu_2204; then
        native_up
      else
        die "需要 Docker，或 Ubuntu 22.04（含 WSL2 里的 Ubuntu 22.04）。当前系统没有这两条路。"
      fi
      ;;
    down)
      if have_docker && [[ -f "$STATE/deploy/docker-compose.sim.yml" ]]; then
        compose stop
        say "容器已停止。数据卷还在。删除卷才用：docker compose -f $STATE/deploy/docker-compose.sim.yml down -v"
      elif ubuntu_2204 && [[ -d "$STATE/src" ]]; then
        bash "$STATE/src/setup/run.sh" lab-stop
      else
        die "没有找到这一台机器上由 urp 启动的工作台。"
      fi
      ;;
    status)
      if have_docker && [[ -f "$STATE/deploy/docker-compose.sim.yml" ]]; then
        compose ps || true
      fi
      curl -fsS "$HEALTH" || die "健康检查失败：${HEALTH}"
      say
      ;;
    fuel)
      install_cli
      local dest
      if have_docker; then
        fetch_compose
        dest="${URP_FUEL_DIR:-$STATE/fuel}"
        bash "$STATE/deploy/fetch-fuel.sh" "$dest"
        export URP_FUEL_DIR="$dest"
        if docker image inspect "$SIM_IMAGE" >/dev/null 2>&1 || pull_sim; then
          compose_files up -d --no-build --pull never --remove-orphans
          say "Fuel 已挂进容器。maze 本来就不需要这些模型。warehouse 与 depot 重新开仿真会话后才会读到。"
        fi
      elif ubuntu_2204; then
        local src
        src="$(clone_src)"
        dest="$src/setup/2026-10-15/cache/ignition-fuel"
        curl -fsSL "${RAW}/deploy/fetch-fuel.sh" -o "$STATE/deploy/fetch-fuel.sh"
        chmod 755 "$STATE/deploy/fetch-fuel.sh"
        bash "$STATE/deploy/fetch-fuel.sh" "$dest"
        say "模型在仓库缓存里。重新启动 warehouse 或 depot 会话后生效。maze 不需要 Fuel。"
      else
        die "下载 Fuel 需要 Docker 或 Ubuntu 22.04。"
      fi
      ;;
    *)
      die "用法：urp up | down | update | status | fuel"
      ;;
  esac
}

route
