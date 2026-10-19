#!/usr/bin/env bash
exec bash "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/../ubuntu/setup.sh" "$@"
