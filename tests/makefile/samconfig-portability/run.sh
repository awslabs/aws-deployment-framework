#!/usr/bin/env bash
# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Entry point for the Makefile message-target portability tests.
#   ./run.sh local      Test the host sed (BSD sed on macOS). No container.
#   ./run.sh docker     Build the image and sweep GNU sed 4.3-4.9 (prefers finch, else docker).
#   ./run.sh container  Alias for 'docker'.
#   ./run.sh all        Run local, then container.
#   ./run.sh precommit  Container sweep on every platform; also local on macOS.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_MAKEFILE="${MAKEFILE:-$(cd "$HERE/../../.." && pwd)/Makefile}"
IMAGE="adf-samconfig-sed-test"

# Resolve the container engine: prefer finch, fall back to docker.
CONTAINER=""
if command -v finch >/dev/null 2>&1; then CONTAINER=finch
elif command -v docker >/dev/null 2>&1; then CONTAINER=docker
fi

run_local() {
  echo '### Local run (host sed)'
  SED_BIN=sed MAKEFILE="$REPO_MAKEFILE" EXAMPLE_TOML="$HERE/samconfig.example.toml" RUN_TOOLING=1 "$HERE/run-checks.sh"
}

run_container() {
  if [ -z "$CONTAINER" ]; then
    echo 'A container engine is required (finch or docker). Install/start one and retry, or skip with:' >&2
    echo '  SKIP=makefile-samconfig-portability git commit ...' >&2
    return 1
  fi
  echo "### Container run (GNU sed 4.3-4.9 matrix, engine: $CONTAINER)"
  "$CONTAINER" build -t "$IMAGE" "$HERE"
  "$CONTAINER" run --rm -v "$REPO_MAKEFILE:/adf/Makefile:ro" "$IMAGE"
}

case "${1:-all}" in
  local)            run_local ;;
  docker|container) run_container ;;
  all)              run_local; echo; run_container ;;
  precommit)        run_container || exit 1; if [ "$(uname -s)" = 'Darwin' ]; then echo; run_local || exit 1; fi ;;
  *) echo "usage: $0 [local|docker|container|all|precommit]" >&2; exit 2 ;;
esac
