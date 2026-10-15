#!/usr/bin/env bash
# Runs in a user-visible desktop terminal. Never logs terminal input.
set -u
setup_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mkdir -p "$setup_dir/runtime" "$setup_dir/logs"
exec 9> "$setup_dir/runtime/interactive-install.lock"
flock -n 9 || { printf 'A Setup terminal is already active.\n'; exit 73; }
printf '%s\n' "$$" > "$setup_dir/runtime/interactive-install.pid"
tty > "$setup_dir/runtime/interactive-install.tty"
printf 'starting\n' > "$setup_dir/runtime/system-install.stage"
printf 'URP Setup: official CycloneDDS for project-local ROS simulation profile\n'
printf 'Enter your password only at the sudo prompt below. Input is hidden.\n'
bash "$setup_dir/install-system.sh"
install_rc=$?
printf '%s\n' "$install_rc" > "$setup_dir/runtime/system-install.exit-code"
if (( install_rc == 0 )); then
  printf 'installed\n' > "$setup_dir/runtime/system-install.stage"
  printf '\nInstallation finished successfully. Codex will continue verification.\n'
else
  printf 'failed\n' > "$setup_dir/runtime/system-install.stage"
  printf '\nInstallation exited with code %s. Codex will inspect the non-secret logs.\n' "$install_rc"
fi
printf 'Press Enter to close this terminal.\n'
read -r close_terminal
exit "$install_rc"
