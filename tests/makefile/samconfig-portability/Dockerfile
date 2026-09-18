# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Builds GNU sed 4.3 (ADF's documented floor) through 4.9 (latest) so the
# message-only Makefile targets can be tested against each. BSD sed (macOS) is
# tested on the host, outside this container.
FROM python:3.12-slim-bookworm

ARG SED_VERSIONS="4.3 4.4 4.5 4.6 4.7 4.8 4.9"
ARG DOCKER_CLI_VERSION=27.3.1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates xz-utils make jq git perl \
    && rm -rf /var/lib/apt/lists/*

# Real (not stubbed) docker CLI so verify_tooling's docker check is genuine.
RUN set -eux; arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64) d=x86_64 ;; arm64) d=aarch64 ;; *) echo "arch $arch?" >&2; exit 1 ;; esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${d}/docker-${DOCKER_CLI_VERSION}.tgz" | tar -xz -C /tmp; \
    install -m0755 /tmp/docker/docker /usr/local/bin/docker; rm -rf /tmp/docker; docker --version

# Build each GNU sed into /opt/sed/<version>/bin/sed.
RUN set -eux; for v in $SED_VERSIONS; do \
      cd /tmp; curl -fsSL "https://ftp.gnu.org/gnu/sed/sed-${v}.tar.xz" -o s.tar.xz; \
      tar -xf s.tar.xz; cd "sed-${v}"; \
      # gnulib references gets(), removed from glibc >= 2.16; drop it so 4.3/4.4 build.
      [ -f lib/stdio.in.h ] && sed -i '/_GL_WARN_ON_USE (gets/d' lib/stdio.in.h || true; \
      ./configure --prefix="/opt/sed/${v}" CFLAGS="-O2 -w" >/dev/null; \
      make -j"$(nproc)" >/dev/null; make install >/dev/null; \
      "/opt/sed/${v}/bin/sed" --version | head -n1; \
      cd /tmp; rm -rf "sed-${v}" s.tar.xz; \
    done

WORKDIR /harness
COPY run-checks.sh sweep.sh samconfig.example.toml /harness/
RUN chmod +x /harness/run-checks.sh /harness/sweep.sh
ENV MAKEFILE=/adf/Makefile EXAMPLE_TOML=/harness/samconfig.example.toml
CMD ["/harness/sweep.sh"]
