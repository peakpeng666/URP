#!/usr/bin/env bash
# Compile the frozen adapted sources only. Never starts a formal experiment.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
if (( $# )); then
  echo 'Usage: bash deploy/build-cohort.sh (requires a complete JDK 17+ and g++ with C++20)' >&2
  exit 2
fi
for tool in java g++; do
  command -v "$tool" >/dev/null || { echo "Missing $tool; install openjdk-17-jdk-headless and g++." >&2; exit 1; }
done
# A JRE may expose jdk.compiler while omitting ct.sym. Test --release 17,
# rather than accepting java --version as proof of a usable JDK.
probe="$(mktemp -d)"
trap 'rm -rf -- "$probe"' EXIT
printf 'final class UrpJdkProbe {}\n' > "$probe/UrpJdkProbe.java"
if ! java -m jdk.compiler/com.sun.tools.javac.Main --release 17 -d "$probe" "$probe/UrpJdkProbe.java"; then
  echo 'AILS needs a complete JDK 17+ supporting --release 17 (Ubuntu: openjdk-17-jdk-headless), not a JRE.' >&2
  exit 1
fi
printf 'Rebuilding AILS and SISR from frozen adapted sources; do not run during timed experiments.\n'
# Keep the frozen build script byte-identical. JDK 17 otherwise decodes source
# comments as US-ASCII in minimal images with LANG=C.
JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dfile.encoding=UTF-8" bash cohort_b/ails/build.sh
bash cohort_b/sisr/build.sh
test -f cohort_b/ails/classes/Adapter/Main.class
test -x cohort_b/sisr/build/sisr_adapter
printf 'AILS and SISR built. This is not a formal research-result validation.\n'
