#!/usr/bin/env bash
# Run from a local terminal. The sudo prompt is deliberately outside all logs.
set -euo pipefail
setup_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mapfile -t packages < "$setup_dir/apt-requested-versions.txt"
apt_options=(-o Dir::Etc::sourcelist=/etc/apt/sources.list
  -o "Dir::Etc::sourceparts=$setup_dir/apt-sources"
  --no-remove --no-install-recommends)
/usr/bin/python3 "$setup_dir/check-apt-plan.py"
LC_ALL=C apt-get "${apt_options[@]}" --simulate install "${packages[@]}" \
  > "$setup_dir/logs/apt-pre-install-simulation.log" 2>&1
grep 'upgraded,' "$setup_dir/logs/apt-pre-install-simulation.log"
printf 'waiting-for-sudo\n' > "$setup_dir/runtime/system-install.stage"
sudo -v
printf 'installing\n' > "$setup_dir/runtime/system-install.stage"
sudo -n env LC_ALL=C apt-get "${apt_options[@]}" --assume-yes install "${packages[@]}" \
  2>&1 | tee "$setup_dir/logs/apt-install.log"
dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' > "$setup_dir/dpkg-after.tsv"
apt-mark showmanual > "$setup_dir/apt-manual-after.txt"
