#!/usr/bin/env bash
# Runs the suite, then builds evidence/: combined MP4 with per-test title cards, key frames, INDEX.md.
set -uo pipefail
cd "$(dirname "$0")"
export URP_BASE_URL="${URP_BASE_URL:-http://127.0.0.1:4100}"
export URP_EVIDENCE_DIR="$(realpath -m "${URP_EVIDENCE_DIR:-./evidence}")"
CJK_FONT="${CJK_FONT:-/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc}"  # macOS: /System/Library/Fonts/PingFang.ttc
mkdir -p "$URP_EVIDENCE_DIR"/{clips,frames}
npx playwright test "$@"; RC=$?
command -v ffmpeg >/dev/null || { echo "ffmpeg missing"; exit $RC; }
RES="$URP_EVIDENCE_DIR/results.json"; LIST="$URP_EVIDENCE_DIR/clips/list.txt"; : > "$LIST"
INDEX="$URP_EVIDENCE_DIR/INDEX.md"
printf '# URP acceptance evidence\n\nBase URL: %s  \nGenerated: %s\n\n| # | Test | Result | Video | Screenshots |\n|---|---|---|---|---|\n' "$URP_BASE_URL" "$(date '+%F %T %Z')" > "$INDEX"
node -e '
const r=require(process.argv[1]);const out=[];
const walk=s=>{(s.specs||[]).forEach(sp=>sp.tests.forEach(t=>{const x=t.results.at(-1)||{};out.push({title:sp.title,status:x.status||"skipped",att:x.attachments||[]});}));(s.suites||[]).forEach(walk);};
r.suites.forEach(walk);
for(const t of out){const v=(t.att.find(a=>a.name==="video")||{}).path||"";const s=t.att.filter(a=>a.contentType==="image/png"&&a.path).map(a=>a.path).join(",");console.log([t.title,t.status,v,s].join("\t"));}
' "$RES" > "$URP_EVIDENCE_DIR/tests.tsv"
i=0
while IFS=$'\t' read -r title status video shots; do
  i=$((i+1)); n=$(printf '%02d' $i)
  printf '%s\n' "$title — $status" > "$URP_EVIDENCE_DIR/clips/$n.title.txt"
  ffmpeg -nostdin -loglevel error -y -f lavfi -i color=c=0x101418:s=1440x900:d=3:r=25 \
    -vf "drawtext=fontfile=$CJK_FONT:textfile=$URP_EVIDENCE_DIR/clips/$n.title.txt:fontcolor=white:fontsize=40:x=(w-tw)/2:y=(h-th)/2" \
    -c:v libx264 -pix_fmt yuv420p "$URP_EVIDENCE_DIR/clips/$n-0title.mp4" && echo "file '$n-0title.mp4'" >> "$LIST"
  if [ -n "$video" ] && [ -f "$video" ]; then
    ffmpeg -nostdin -loglevel error -y -i "$video" -vf "scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,fps=25" \
      -c:v libx264 -pix_fmt yuv420p -an "$URP_EVIDENCE_DIR/clips/$n-1test.mp4" && echo "file '$n-1test.mp4'" >> "$LIST"
    ffmpeg -nostdin -loglevel error -y -i "$video" -vf "select='gt(scene,0.3)',scale=720:-1" -vsync vfr -frames:v 12 "$URP_EVIDENCE_DIR/frames/$n-%02d.png"
  fi
  sl=$(echo "$shots" | tr ',' '\n' | sed '/^$/d' | sed "s|^$URP_EVIDENCE_DIR/||" | awk '{printf "[%s](%s)<br>", NR, $0}')
  printf '| %s | %s | %s | %s | %s |\n' "$n" "$title" "$status" "${video#$URP_EVIDENCE_DIR/}" "$sl" >> "$INDEX"
done < "$URP_EVIDENCE_DIR/tests.tsv"
(cd "$URP_EVIDENCE_DIR/clips" && ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i list.txt -c copy ../acceptance.mp4)
printf '\nCombined video: acceptance.mp4  \nKey frames: frames/  \nHTML report: html/index.html  \nPlaywright exit code: %s\n' "$RC" >> "$INDEX"
echo "Evidence: $URP_EVIDENCE_DIR (INDEX.md, acceptance.mp4)"; exit $RC
