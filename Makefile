# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Makefile versions
MAKEFILE_VERSION := 2.0
UPDATE_VERSION := make/latest

# Repository versions
SRC_VERSION := $(shell git describe --tags --match 'v[0-9]*')
SRC_VERSION_TAG_ONLY := $(shell git describe --tags --abbrev=0 --match 'v[0-9]*')

# ADF Related URLs
SRC_URL_BASE := https://github.com/awslabs/aws-deployment-framework
RAW_URL_BASE := https://raw.githubusercontent.com/awslabs/aws-deployment-framework

UPDATE_URL := "$(RAW_URL_BASE)/$(UPDATE_VERSION)/Makefile"
SRC_TAGGED_URL_BASE := "$(SRC_URL_BASE)/tree/$(SRC_VERSION_TAG_ONLY)"
MAKE_TAGGED_URL_BASE := "$(SRC_URL_BASE)/tree/make/$(MAKEFILE_VERSION)"

# Command line colors
CLR_RED := $(shell printf "\033[0;31m")
CLR_GREEN := $(shell printf "\033[0;32m")
CLR_YELLOW := $(shell printf "\033[0;33m")
CLR_BLUE := $(shell printf "\033[0;34m")
CLR_END := $(shell printf "\033[0m")

# Files to work with
SAM_VERSIONED_TEMPLATE := ./src/template-sam.yml
SAM_BUILD_DIR := ./.aws-sam/build
SRC_DIR := ./src

REQUIREMENTS := $(shell find . -maxdepth 1 -name 'requirements.txt' -or -name 'requirements-dev.txt')
SRC_REQUIREMENTS := $(shell find $(SRC_DIR) -name 'requirements.txt' -or -name 'requirements-dev.txt')
PIP_INSTALL_REQUIREMENTS := $(addprefix -r ,$(REQUIREMENTS))
PIP_INSTALL_SRC_REQUIREMENTS := $(addprefix -r ,$(SRC_REQUIREMENTS))

# Actions

# Default action should come first, jump to build:
all: build

# Which actions do not create an actual file like make expects:
.PHONY: all clean update_makefile
.PHONY: report_makefile_version report_versions version_report
.PHONY: build_debs deps src_deps docker version_number git_ignore docs tox
.PHONY: pre_build pre_deps_build sam_build post_build build deps_build
.PHONY: pre_deploy_msg pre_deploy sam_deploy post_deploy deploy

.venv: .venv/is_ready

.venv/is_ready:
	( \
		test -d .venv || python3 -m venv .venv; \
		touch .venv/is_ready; \
	)

clean:
	test -e $(SAM_VERSIONED_TEMPLATE) && rm $(SAM_VERSIONED_TEMPLATE) || exit 0
	test -d $(SAM_BUILD_DIR) && rm -r $(SAM_BUILD_DIR) || exit 0
	test -d .venv && rm -r .venv || exit 0

update_makefile: report_makefile_version
	@( \
		( \
			which curl && curl -fsSL $(UPDATE_URL) -o ./Makefile.new \
		) || ( \
			which wget && wget -q $(UPDATE_URL) -O ./Makefile.new \
		) || ( \
			echo "$(CLR_RED)No curl or wget, please install and try again$(CLR_END)" && \
			exit 1 \
		); \
	)
	@echo "Updated Makefile info:"
	@make -f ./Makefile.new clean build_deps report_makefile_version
	@mv ./Makefile.new ./Makefile
	@echo "$(CLR_GREEN)Update complete$(CLR_END)"

report_makefile_version:
	@echo "Makefile: v$(MAKEFILE_VERSION) $$(shasum --algorithm 256 Makefile)"

report_versions: report_makefile_version
	@echo "$(CLR_YELLOW)*** Beginning of ADF Version Report ***$(CLR_END)"
	@echo "ADF Source version: $(SRC_VERSION)"
	@echo "ADF $$(cat src/template.yml | grep SemanticVersion | xargs)"
	@echo ""
	@echo "Hardware platform: $$(uname --hardware-platform || echo 'n/a')"
	@echo "Kernel name: $$(uname --kernel-name || echo 'n/a')"
	@echo "Kernel release: $$(uname --kernel-release || echo 'n/a')"
	@echo ""
	@test -e /etc/os-release && echo "OS Release:" && cat /etc/os-release
	@echo ""
	@echo "Disk:"
	@df -h $$PWD || echo 'N/A'
	@echo ""
	@echo "Dependencies:"
	@echo "docker: $$(docker --version || echo 'n/a')"
	@echo "git: $$(git --version || echo 'n/a')"
	@echo "make: $$(make --version || echo 'n/a')"
	@( \
		. .venv/bin/activate; \
		pip --version; \
		pip list; \
	)
	@echo ""
	git status
	@echo "$(CLR_YELLOW)*** End of ADF Version Report ***$(CLR_END)"

version_report: report_versions

build_deps: .venv
	( \
		. .venv/bin/activate; \
		pip install aws-sam-cli yq; \
	)

deps: .venv
	( \
		. .venv/bin/activate; \
		pip install $(PIP_INSTALL_REQUIREMENTS); \
	)

src_deps: .venv
	( \
		. .venv/bin/activate; \
		pip install $(PIP_INSTALL_SRC_REQUIREMENTS); \
	)

tox: deps
	# Run tests via tox
	@( \
		. .venv/bin/activate; \
		tox --version; \
		tox; \
	)

docker:
	@echo "Prepare docker to support all architectures..."
	docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

version_number: .venv
	@echo "Generate a new version number..."
	cp $(SRC_DIR)/template.yml $(SAM_VERSIONED_TEMPLATE)
	( \
		. .venv/bin/activate; \
		BASE_ADF_VERSION=$$(cat $(SAM_VERSIONED_TEMPLATE) | yq '.Metadata."AWS::ServerlessRepo::Application".SemanticVersion' -r); \
		COMMIT_ADF_VERSION=$(SRC_VERSION); \
		sed "s/Version: $$BASE_ADF_VERSION/Version: $$COMMIT_ADF_VERSION/g" -i $(SAM_VERSIONED_TEMPLATE); \
	)

git_ignore:
	mkdir -p $(SAM_BUILD_DIR)/InitialCommitHandler/bootstrap_repository/adf-bootstrap/deployment/lambda_codebase/initial_commit/pipelines_repository
	cp $(SRC_DIR)/lambda_codebase/initial_commit/bootstrap_repository/adf-bootstrap/deployment/lambda_codebase/initial_commit/pipelines_repository/.gitignore $(SAM_BUILD_DIR)/InitialCommitHandler/bootstrap_repository/adf-bootstrap/deployment/lambda_codebase/initial_commit/pipelines_repository/.gitignore
	cp $(SRC_DIR)/lambda_codebase/initial_commit/bootstrap_repository/.gitignore $(SAM_BUILD_DIR)/InitialCommitHandler/bootstrap_repository/.gitignore

docs:
	@echo ""
	@echo "$(CLR_YELLOW)Please use the guides related to ADF $(SRC_VERSION_TAG_ONLY):$(CLR_END)"
	@echo ""
	@( \
		echo "$(SRC_VERSION_TAG_ONLY)" | grep -E 'v[0-3]\.' &> /dev/null && \
		echo "* $(CLR_BLUE)$(MAKE_TAGGED_URL_BASE)/docs/installation-guide.md$(CLR_END)" || \
		echo "* $(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/installation-guide.md$(CLR_END)"; \
	)
	@echo ""
	@echo "* $(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/admin-guide.md$(CLR_END)"
	@echo ""
	@echo "* $(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/user-guide.md$(CLR_END)"
	@echo ""

pre_build: build_deps docker version_number git_ignore

pre_deps_build: deps docker version_number git_ignore

sam_build:
	@( \
		. .venv/bin/activate; \
		sam build \
			--use-container \
			--template $(SAM_VERSIONED_TEMPLATE); \
	)

post_build:
	@rm $(SAM_VERSIONED_TEMPLATE)
	@echo ""
	@echo "$(CLR_GREEN)ADF built successfully!$(CLR_END)"
	@echo "$(CLR_GREEN)To deploy ADF, please run:$(CLR_END) make deploy"
	@echo ""

build: pre_build sam_build post_build

deps_build: pre_deps_build sam_build post_build

pre_deploy_msg:
	@echo ""
	@echo ""
	@echo "$(CLR_GREEN)Thank you for deploying ADF, we are about to proceed$(CLR_END)"
	@echo ""
	@echo "$(CLR_YELLOW)In the next step, a few questions need to be answered.$(CLR_END)"
	@echo "$(CLR_YELLOW)Please use the following guide to answer these:$(CLR_END)"
	@echo ""
	@( \
		echo "$(SRC_VERSION_TAG_ONLY)" | grep -E 'v[0-3]\.' &> /dev/null && \
		echo "$(CLR_BLUE)$(MAKE_TAGGED_URL_BASE)/docs/installation-guide.md$(CLR_END)" || \
		echo "$(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/installation-guide.md$(CLR_END)"; \
	)
	@echo ""
	@echo ""

pre_deploy: build_deps pre_deploy_msg

sam_deploy:
	@( \
		. .venv/bin/activate; \
		sam deploy \
			--guided \
			--capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
			--no-disable-rollback \
			--tags "ADF_VERSION=$(SRC_VERSION)"; \
	)

post_deploy: docs

deploy: pre_deploy sam_deploy post_deploy
