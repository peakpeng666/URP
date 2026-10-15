#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p classes
find adapted/src -name '*.java' | sort > sources.list
java -m jdk.compiler/com.sun.tools.javac.Main --release 17 -d classes @sources.list
