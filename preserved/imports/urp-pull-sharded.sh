#!/usr/bin/env bash
# Pull gdrive:URP into ~/Desktop/URP using per-directory shards so each rclone
# process lists only its own subtree instead of serialising one 80k listing.
set -uo pipefail

SRC='gdrive:URP'
DST='/home/peakpeng/Desktop/URP'
LOGDIR='/tmp/urp-pull'
mkdir -p "$LOGDIR"

COMMON=(
  --fast-list
  --checkers 32
  --multi-thread-streams 4
  --multi-thread-cutoff 64M
  --buffer-size 16M
  --timeout 300s
  --contimeout 60s
  --retries 3
  --low-level-retries 20
  --stats 60s
  --stats-one-line
  --log-level INFO
)

start() {
  local name="$1" src="$2" dst="$3" transfers="$4"
  shift 4
  nohup rclone copy "$src" "$dst" "${COMMON[@]}" --transfers "$transfers" \
    --log-file "$LOGDIR/$name.log" "$@" \
    >"$LOGDIR/$name.out" 2>&1 &
  printf '%s pid=%s transfers=%s\n' "$name" "$!" "$transfers"
}

start heavy-gongcheng "$SRC/工程文件" "$DST/工程文件" 16
start heavy-daima     "$SRC/代码"     "$DST/代码"     16
start mid-lishi       "$SRC/历史资料" "$DST/历史资料" 8
start rest "$SRC" "$DST" 8 \
  --exclude '/工程文件/**' --exclude '/代码/**' --exclude '/历史资料/**'

sleep 2
echo "=== running rclone copy procs ==="
ps -o pid=,args= -C rclone 2>/dev/null | grep -c 'copy gdrive:URP'
