#!/usr/bin/env bash
# Build and validate the checked-out revision before publishing any tag.
set -euo pipefail
cd "$(dirname "$0")/.."

name="${1:?bench or sim}"
dockerfile="${2:?dockerfile}"
[[ "$name" == bench || "$name" == sim ]] || { echo 'Expected bench or sim' >&2; exit 2; }
owner="$(printf '%s' "${GITHUB_REPOSITORY_OWNER:?}" | tr '[:upper:]' '[:lower:]')"
image="ghcr.io/${owner}/urp-${name}"
sha="${GITHUB_SHA:?}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'GITHUB_SHA must be a full commit SHA' >&2; exit 2; }
[[ "$(git rev-parse HEAD)" == "$sha" ]] || { echo 'Checkout and GITHUB_SHA disagree' >&2; exit 2; }
source_url="${SOURCE:-https://github.com/peakpeng666/URP}"

# Dispatch on redo/another branch publishes only its immutable SHA.
# It must not silently replace the deploy or latest channel.
tags=("$sha")
if [[ "${GITHUB_REF:-}" == refs/tags/v* ]]; then
  tags+=("${GITHUB_REF#refs/tags/}" latest)
elif [[ "${GITHUB_REF:-}" == refs/heads/deploy ]]; then
  tags+=(deploy)
fi

args=()
for tag in "${tags[@]}"; do
  args+=(-t "${image}:${tag}")
done

docker build -f "$dockerfile" \
  --build-arg "URP_REVISION=${sha}" \
  --label "org.opencontainers.image.source=${source_url}" \
  --label "org.opencontainers.image.revision=${sha}" \
  --label "org.opencontainers.image.title=urp-${name}" \
  "${args[@]}" .

bash deploy/test-image.sh "${image}:${sha}" "$sha" "$name" \
  "${URP_IMAGE_TEST_OUTPUT:-.local-state/image-${name}}"

for tag in "${tags[@]}"; do
  docker push "${image}:${tag}"
done

