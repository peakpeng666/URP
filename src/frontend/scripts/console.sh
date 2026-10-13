#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_ROOT"

usage() {
  cat <<'USAGE'
BPP 科研工作台 — 从项目相对路径执行，可在任意当前目录调用。
  bash scripts/console.sh setup [--python-only]  安装锁定依赖
  bash scripts/console.sh browser-setup [--with-deps]  安装独立浏览器验收依赖
  bash scripts/console.sh data-convert           校验/解压原始 ZIP 并转换静态数据
  bash scripts/console.sh validate [args]        执行全量科学数据核验
  bash scripts/console.sh dev [args]             localhost 开发服务
  bash scripts/console.sh build [args]           构建离线静态应用
  bash scripts/console.sh test [args]            Python/内核测试；有 test:ui 则同时运行
  bash scripts/console.sh serve [args]           localhost 构建预览，默认端口 4173
  bash scripts/console.sh package [args]         源码、输入 ZIP 与验收证据打包

首次运行顺序：setup → data-convert → validate → test → build → serve。
依赖安装需要网络；完成安装和转换后的工作台无需云服务。
USAGE
}

require_python() {
  [[ -x .venv/bin/python ]] || { printf 'Run bash scripts/console.sh setup first.\n' >&2; exit 1; }
}
require_frontend() {
  [[ -f package.json ]] || { printf '前端尚未接入：缺少 package.json。数据转换、科学核验与内核测试可独立执行。\n' >&2; exit 1; }
  command -v node >/dev/null || { printf 'Node.js is required; run setup.\n' >&2; exit 1; }
  node -e 'const p=require("./package.json"); if(!p.scripts?.[process.argv[1]]) { console.error("前端尚未接入 npm script:", process.argv[1]); process.exit(1); }' "$1"
}
command_name="${1:-help}"
if (( $# )); then shift; fi
case "$command_name" in
  setup) exec bash scripts/setup.sh "$@" ;;
  browser-setup)
    [[ -f tools/browser/package.json && -f tools/browser/package-lock.json ]] || {
      printf 'Missing locked browser verification dependencies under tools/browser/.\n' >&2; exit 1;
    }
    npm ci --prefix tools/browser --engine-strict --no-audit --no-fund
    exec node tools/browser/node_modules/playwright/cli.js install chromium "$@"
    ;;
  data-convert)
    require_python
    if (( $# )); then printf 'Use individual Python scripts for custom data paths.\n' >&2; exit 2; fi
    .venv/bin/python scripts/import_data.py
    exec .venv/bin/python scripts/convert_data.py
    ;;
  validate)
    require_python
    .venv/bin/python scripts/validate_data.py "$@"
    # Only the default data paths can be refreshed automatically. set -e preserves
    # validator failure and prevents trusted UI metadata from being refreshed then.
    if (( $# == 0 )) && [[ -f public/data/meta.json ]]; then
      .venv/bin/python scripts/convert_data.py --refresh-validation
    fi
    ;;
  dev) require_frontend dev; exec npm run dev -- --host 127.0.0.1 "$@" ;;
  build) require_frontend build; exec npm run build -- "$@" ;;
  test)
    require_python
    .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
    shopt -s nullglob
    node_tests=(tests/*.mjs)
    (( ${#node_tests[@]} )) || { printf 'No Node tests found.\n' >&2; exit 1; }
    node --test "$@" "${node_tests[@]}"
    node --test core/routing/tests/*.test.js
    if [[ -f package.json ]]; then npm run --if-present test:ui; fi
    ;;
  serve) require_frontend preview; exec npm run preview -- --host 127.0.0.1 --port "${BPP_PORT:-4173}" "$@" ;;
  package) require_python; exec .venv/bin/python scripts/package_delivery.py "$@" ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
