#!/usr/bin/env bash
# Uses the user's configured PATH adapter (Ghostty), including cwd/title handling.
set -euo pipefail
urp_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
terminal_exe="$(command -v x-terminal-emulator)"
exec "$terminal_exe" --wait --title="URP — ${1:-help}" --working-directory="$urp_root" \
  -- bash "$urp_root/setup/run.sh" "$@"
