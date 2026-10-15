#!/usr/bin/env bash
# Respect the user's configured terminal adapter on PATH (currently Ghostty).
set -euo pipefail
setup_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
terminal_exe="$(command -v x-terminal-emulator)"
exec "$terminal_exe" --wait --title='URP Setup — 系统依赖安装' \
  --working-directory="$setup_dir/../.." -- bash "$setup_dir/interactive-install.sh"
