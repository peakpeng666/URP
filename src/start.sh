#!/usr/bin/env bash
set -euo pipefail
URP_SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "${1:-help}" in
  backend|后端)
    cd "$URP_SRC/backend"
    exec .venv/bin/python -m backend serve --import-root packages --port "${URP_API_PORT:-4180}"
    ;;
  frontend|前端)
    exec bash "$URP_SRC/frontend/scripts/console.sh" serve
    ;;
  build|构建)
    exec bash "$URP_SRC/frontend/scripts/console.sh" build
    ;;
  *) printf 'Usage: bash src/start.sh backend | frontend | build\n';;
esac
