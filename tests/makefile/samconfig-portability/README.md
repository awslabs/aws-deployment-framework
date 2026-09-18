# Makefile `samconfig.toml` sed-portability harness

This harness tests **only the message-producing Makefile targets** across many
`sed` implementations. It never runs `make build` or `make deploy`.

## Why this exists

The `post_deploy_msg` target parses `samconfig.toml` with three `sed -nE`
extractions (`stack_name`, `region`, and `DeploymentAccountMainRegion`), each
with a literal fallback when the value is absent. That parsing depends on `sed`
behaviour that differs between BSD `sed` (the default on macOS) and GNU `sed`
(on Linux). This harness pins that behaviour down so a regression in the
next-steps message, the version report, or the tooling check is caught early —
without the cost of a full build or deploy.

The targets under test are:

- `post_deploy_msg` — `samconfig.toml` parsing plus the fallback path.
- `report_makefile_version` — the version string.
- `verify_tooling` — the tooling check (not `sed`-version sensitive; run once).

## Usage

```sh
./run.sh local      # host sed (BSD sed on macOS). No container.
./run.sh docker     # build the image and sweep GNU sed 4.3-4.9 (finch if installed, else docker).
./run.sh container  # alias for 'docker'.
./run.sh all        # local, then container.
./run.sh precommit  # container sweep everywhere; also local on macOS.
```

## BSD sed vs GNU sed

BSD `sed` is intentionally **not** part of the container matrix — the container
only builds and sweeps GNU `sed` 4.3 through 4.9. BSD `sed` coverage comes from
the **macOS host run** (`./run.sh local`), which is the ground truth for BSD
behaviour. Run the local check on macOS to validate the BSD path.

## Pre-commit hook

A pre-commit hook (`.pre-commit-config.yaml` at the repository root) runs this
harness automatically when the `Makefile` is staged. It runs the container sweep
on every platform and additionally the local BSD-sed check on macOS. The
container path uses `finch` if installed, otherwise `docker`, so a container
engine (finch or docker) is required for the sweep. Enable it once per clone:

```sh
pip install pre-commit && pre-commit install
```

### Caveat: redirected `core.hooksPath`

If `core.hooksPath` is redirected to another tool (for example by Amazon
git-defender), the standard pre-commit hook may not fire. In that case the check
must be wired into that tool's own extension point instead, otherwise the
harness will silently not run on commit.
