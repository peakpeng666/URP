#!/usr/bin/env bash
# Called only inside the private-log supervisor. No package output goes public.
set -euo pipefail
source_root="${1:?source root}"
private="${2:?private directory}"
cd "$source_root"
[[ "$(git rev-parse HEAD)" == 94420cf3b703c564134048e1b074406df901bba3 ]]
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
python3 "$(dirname "$0")/verify_registry.py" "$source_root" > "$private/registry-identity.json"
bash setup/ubuntu/setup.sh --components workbench --fields2cover skip
