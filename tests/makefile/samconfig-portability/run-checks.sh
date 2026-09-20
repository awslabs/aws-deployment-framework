#!/usr/bin/env bash
# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Test ONLY the message-producing Makefile targets against a given sed:
#   post_deploy_msg (samconfig.toml parsing + fallback), report_makefile_version
#   (version), verify_tooling (tooling check). Never runs `make build`/`make deploy`.
set -uo pipefail

SED_BIN="${SED_BIN:-sed}"
MAKEFILE="${MAKEFILE:?Set MAKEFILE to the Makefile under test}"
EXAMPLE_TOML="${EXAMPLE_TOML:-}"
RUN_TOOLING="${RUN_TOOLING:-1}"

sed_dir=""
case "$SED_BIN" in */*) sed_dir="$(cd "$(dirname "$SED_BIN")" && pwd)" ;; esac

fail=0
pass() { printf '  \033[0;32mPASS\033[0m %s\n' "$1"; }
bad()  { printf '  \033[0;31mFAIL\033[0m %s\n' "$1"; fail=1; }

run_target() {
  if [ -n "$sed_dir" ]; then
    PATH="$sed_dir:$PATH" make --no-print-directory -C "$WORKDIR" "$1" 2>/dev/null
  else
    make --no-print-directory -C "$WORKDIR" "$1" 2>/dev/null
  fi
}

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/adf-sed.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT
cp "$MAKEFILE" "$WORKDIR/Makefile"

if "$SED_BIN" --version >/dev/null 2>&1; then
  echo "== sed: $("$SED_BIN" --version 2>/dev/null | head -n1)"
else
  echo "== sed: BSD/non-GNU sed ($SED_BIN)"
fi

# Scenario A: populated samconfig.toml with sentinel values.
cat > "$WORKDIR/samconfig.toml" <<'EOF'
version = 0.1
[default.deploy.parameters]
stack_name = "sentinel-stack-name"
parameter_overrides = "DeploymentAccountId=\"111111111111\" DeploymentAccountMainRegion=\"sentinel-main-region\" DeploymentAccountTargetRegions=\"us-east-1\""
[default.global.parameters]
region = "sentinel-deploy-region"
EOF
out="$(run_target post_deploy_msg)"
echo "$out" | grep -q 'filteringText=sentinel-stack-name' && pass 'stack_name -> CloudFormation URL' || bad 'stack_name not substituted'
echo "$out" | grep -q 'Wait for the sentinel-stack-name stack' && pass 'stack_name -> heading text' || bad 'stack_name heading missing'
echo "$out" | grep -q 'region=sentinel-deploy-region' && pass 'region -> management-account URLs' || bad 'deploy region not substituted'
echo "$out" | grep -q 'sentinel-main-region.console.aws' && pass 'main region -> deployment-account host' || bad 'main region host not substituted'
echo "$out" | grep -q 'YOUR_MAIN_REGION' && bad 'fallback leaked while populated' || pass 'no fallback leak when populated'

# Scenario B: samconfig.toml absent -> fallbacks.
rm -f "$WORKDIR/samconfig.toml"
out="$(run_target post_deploy_msg)"
echo "$out" | grep -q 'filteringText=serverlessrepo-aws-deployment-framework' && pass 'fallback stack name' || bad 'fallback stack name missing'
echo "$out" | grep -q 'region=us-east-1' && pass 'fallback deploy region' || bad 'fallback deploy region missing'
echo "$out" | grep -q 'Replace .*YOUR_MAIN_REGION' && pass 'fallback main-region guidance' || bad 'fallback main-region guidance missing'

# Scenario C: the faithful example fixture.
if [ -n "$EXAMPLE_TOML" ] && [ -f "$EXAMPLE_TOML" ]; then
  cp "$EXAMPLE_TOML" "$WORKDIR/samconfig.toml"
  out="$(run_target post_deploy_msg)"
  echo "$out" | grep -q 'filteringText=example-adf-stack' && pass 'example: stack_name' || bad 'example: stack_name'
  echo "$out" | grep -q 'eu-west-1.console.aws' && pass 'example: main region eu-west-1' || bad 'example: main region'
  rm -f "$WORKDIR/samconfig.toml"
fi

# Version check.
expected="$(command sed -nE 's/^MAKEFILE_VERSION[[:space:]]*:=[[:space:]]*([0-9.]+).*/\1/p' "$WORKDIR/Makefile" | head -n1)"
run_target report_makefile_version | grep -q "v${expected}" && pass "report_makefile_version -> v${expected}" || bad "version mismatch (want v${expected})"

# Tooling check (run once; needs full toolchain present).
if [ "$RUN_TOOLING" = "1" ]; then
  if run_target verify_tooling >/dev/null 2>&1; then pass 'verify_tooling passes'; else bad 'verify_tooling failed'; fi
fi

exit $fail
