#!/usr/bin/env bash
# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Container entrypoint: run run-checks.sh against the base-image sed plus every
# GNU sed built into /opt/sed/*/bin/sed. verify_tooling runs only on the first
# pass (it is not sed-version sensitive).
set -uo pipefail
overall=0
run_one() { SED_BIN="$1" RUN_TOOLING="$2" /harness/run-checks.sh || overall=1; echo; }
run_one "sed" 1
for d in /opt/sed/*/bin/sed; do [ -x "$d" ] || continue; run_one "$d" 0; done
exit $overall
