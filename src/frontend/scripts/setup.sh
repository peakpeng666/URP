#!/usr/bin/env bash
# Run from any directory. Dependencies live in this project, never the system Python.
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_ROOT"

python_only=0
case "${1:-}" in
  --python-only) python_only=1; shift ;;
  "") ;;
  *) printf 'Usage: bash scripts/setup.sh [--python-only]\n' >&2; exit 2 ;;
esac
if (( $# )); then printf 'Unexpected setup arguments.\n' >&2; exit 2; fi

PYTHON_COMMAND="${BPP_PYTHON:-python3}"
command -v "$PYTHON_COMMAND" >/dev/null || { printf 'Python 3.10–3.13 is required.\n' >&2; exit 1; }
"$PYTHON_COMMAND" -c 'import sys; assert (3, 10) <= sys.version_info < (3, 14), "Use Python 3.10–3.13 for the locked NumPy wheels"'
if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_COMMAND" -m venv .venv || {
    printf 'Virtual environment creation failed. On Ubuntu 22.04 install python3-venv, then retry.\n' >&2
    exit 1
  }
fi
.venv/bin/python -c 'import sys; assert sys.prefix != sys.base_prefix, "Expected isolated .venv"; assert (3, 10) <= sys.version_info < (3, 14)'
.venv/bin/python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r requirements.lock
.venv/bin/python -c 'import sys, numpy; print("Python:", sys.version.split()[0], "NumPy:", numpy.__version__, "environment:", sys.prefix)'

if (( ! python_only )); then
  command -v node >/dev/null || { printf 'Node.js is required; see docs/MIGRATION.md.\n' >&2; exit 1; }
  command -v npm >/dev/null || { printf 'npm is required; see docs/MIGRATION.md.\n' >&2; exit 1; }
  [[ -f package.json && -f package-lock.json ]] || {
    printf 'package.json and package-lock.json are required. During frontend development use setup --python-only.\n' >&2
    exit 1
  }
  npm ci --engine-strict --no-audit --no-fund
  printf 'Node: %s; npm: %s\n' "$(node --version)" "$(npm --version)"
fi
printf 'Setup completed. Next: bash scripts/console.sh data-convert\n'
