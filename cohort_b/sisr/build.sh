#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
g++ -std=c++20 -O3 adapted/src/ProblemInstance.cpp adapted/src/Solution.cpp adapted/src/Sisrs.cpp adapted/src/adapter_main.cpp -o build/sisr_adapter
