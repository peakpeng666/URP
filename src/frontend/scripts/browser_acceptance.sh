#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
# First run console.sh browser-setup, build, and serve in a second terminal.
# Deliberately serial: browser timing assertions should not compete for CPU.
base=http://127.0.0.1:4173
mkdir -p artifacts/final-browser-logs
for script in product-visual overview-check product-errors product-browse product-functional product-mobile product-evidence canvas-audit curve-audit; do
  printf 'Browser suite: %s\n' "$script"
  node "tools/browser/$script.mjs" "$base" > "artifacts/final-browser-logs/$script.log" 2>&1
done
node tools/browser/zoom-check.mjs "$base" artifacts/codex-browser/product-browser-zoom > artifacts/final-browser-logs/zoom-overview.log 2>&1
node tools/browser/zoom-check.mjs "$base/#/replay/confirmation_weibull_3_45_r0__descending?a=SELECTOR&b=SBS&t=500" artifacts/codex-browser/product-replay-browser-zoom > artifacts/final-browser-logs/zoom-replay.log 2>&1
python3 scripts/summarize_acceptance.py
