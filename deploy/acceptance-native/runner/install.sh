#!/usr/bin/env bash
# Called only inside the private-log supervisor. No package output goes public.
set -euo pipefail
source_root="${1:?source root}"
private="${2:?private directory}"
# Keep control traces separate from verbose dependency output so bounded reads
# cannot lose the phase marker while a long-running command remains active.
exec 3> "$private/installation-trace.log"
export BASH_XTRACEFD=3
phase() { printf 'URP_INSTALL_PHASE %s\n' "$1" >&3; }
phase source_identity
cd "$source_root"
[[ "$(git rev-parse HEAD)" == 4423a4f9731cbb099433b565f3daa0b41af67f49 ]]
python3 "$(dirname "$0")/verify_worktree.py" "$source_root" > "$private/source-identity.json"
[[ "$(uname -m)" == x86_64 ]]
# The existing installer itself checks Ubuntu 22.04 and rejects root execution.
# Prevent official uv installer from changing shell profiles.
export UV_NO_MODIFY_PATH=1
export HOME="$private/home"
mkdir -p "$HOME/.local/bin"
export UV_INSTALL_DIR="$HOME/.local/bin"
export PATH="$UV_INSTALL_DIR:$PATH"
export GIT_TERMINAL_PROMPT=0
# Explicitly isolate Python installer state; no persisted package caches uploaded.
export UV_CACHE_DIR="$private/uv-cache"
export UV_PYTHON_INSTALL_DIR="$private/python"
phase registry_check
python3 "$(dirname "$0")/verify_registry.py" "$source_root" > "$private/registry-identity.json"
# Xtrace is private; reducer publishes only a fixed installation-step enum.
export PS4='+URP_SETUP '
set +e
phase setup
bash -x setup/ubuntu/setup.sh --components workbench --fields2cover skip
setup_exit=$?
set -e
run_host_apt_repair() {
  phase apt_repair
  python3 "$(dirname "$0")/host_apt_repair.py" --source "$source_root" --private-dir "$private" --setup-exit "$setup_exit"
}
if [[ "$setup_exit" == 100 ]]; then
  # Original exit is retained; simulation diagnostics cannot make failure pass.
  phase apt_diagnostic
  python3 "$(dirname "$0")/apt_diagnostic.py" "$source_root" "$private" || true
  if [[ "${URP_HOST_APT_REPAIR:-}" == 1 ]] && run_host_apt_repair; then
    # One retry only, still the unchanged pinned installer and original options.
    set +e
    phase setup
    bash -x setup/ubuntu/setup.sh --components workbench --fields2cover skip
    setup_exit=$?
    set -e
    if [[ "$setup_exit" == 100 ]]; then
      phase apt_diagnostic
      python3 "$(dirname "$0")/apt_diagnostic.py" "$source_root" "$private" || true
    fi
  fi
fi
if [[ "$setup_exit" == 0 ]]; then phase complete; fi
exit "$setup_exit"
