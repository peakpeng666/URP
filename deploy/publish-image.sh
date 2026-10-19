#!/usr/bin/env bash
# Used by .github/workflows/images.yml. Tags the image for the deploy branch
# or a v* release and records the repository link GitHub uses for packages.
set -euo pipefail

name="${1:?bench or sim}"
dockerfile="${2:?dockerfile}"
owner="$(printf '%s' "${GITHUB_REPOSITORY_OWNER:?}" | tr '[:upper:]' '[:lower:]')"
image="ghcr.io/${owner}/urp-${name}"
sha="${GITHUB_SHA:?}"
source_url="${SOURCE:-https://github.com/peakpeng666/URP}"

tags=()
if [[ "${GITHUB_REF:-}" == refs/tags/v* ]]; then
  tags+=("${GITHUB_REF#refs/tags/}" latest "$sha")
else
  tags+=(deploy "$sha")
fi

args=()
for tag in "${tags[@]}"; do
  args+=(-t "${image}:${tag}")
done

docker build -f "$dockerfile" \
  --label "org.opencontainers.image.source=${source_url}" \
  --label "org.opencontainers.image.revision=${sha}" \
  --label "org.opencontainers.image.title=urp-${name}" \
  "${args[@]}" \
  .

for tag in "${tags[@]}"; do
  docker push "${image}:${tag}"
done
