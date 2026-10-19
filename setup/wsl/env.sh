#!/usr/bin/env bash
# Compatibility wrapper. The shared Ubuntu 22.04 setup lives in setup/ubuntu/.
# shellcheck source=../ubuntu/env.sh
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/../ubuntu/env.sh"
