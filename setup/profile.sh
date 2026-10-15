#!/usr/bin/env bash
# Process-scoped settings only. Does not edit login shells, ROS, or system Python.
set -euo pipefail
profile="${1:-help}"
if (( $# )); then shift; fi
case "$profile" in
  research)
    export URP_WORKERS="${URP_WORKERS:-12}"
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
    ;;
  numpy)
    export URP_WORKERS=1
    export OMP_NUM_THREADS="${URP_BLAS_THREADS:-12}" OPENBLAS_NUM_THREADS="${URP_BLAS_THREADS:-12}"
    export MKL_NUM_THREADS="${URP_BLAS_THREADS:-12}" NUMEXPR_NUM_THREADS="${URP_BLAS_THREADS:-12}"
    ;;
  frontend)
    export RAYON_NUM_THREADS="${URP_BUILD_THREADS:-4}"
    ;;
  simulation)
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
    export RMW_IMPLEMENTATION="${URP_RMW:-rmw_cyclonedds_cpp}"
    export ROS_DOMAIN_ID="${URP_ROS_DOMAIN_ID:-139}" ROS_LOCALHOST_ONLY=1
    profile_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    export CYCLONEDDS_URI="${CYCLONEDDS_URI:-file://$profile_dir/cyclonedds.xml}"
    ;;
  *) printf 'Usage: bash setup/profile.sh research|numpy|frontend|simulation COMMAND [ARGS...]\n'; exit 2 ;;
esac
(( $# )) || { printf 'A command is required.\n' >&2; exit 2; }
exec "$@"
