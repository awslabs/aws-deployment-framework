# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

# Makefile versions
MAKEFILE_VERSION := 2.3.4
UPDATE_VERSION := make/latest

# If you change this Makefile, run:
#   ./tests/makefile/samconfig-portability/run.sh docker  # GNU sed 4.3-4.9 (finch if installed, else docker)
#   ./tests/makefile/samconfig-portability/run.sh local   # host sed (BSD on macOS)
# A pre-commit hook (.pre-commit-config.yaml) runs these automatically when the
# Makefile is staged (container sweep everywhere, plus the local check on macOS).

# This Makefile requires Python version 3.9 or later, and the interpreter
# must include the tarfile data_filter for safe tar extraction (PEP 706).
REQUIRED_PYTHON_MAJOR_VERSION := 3
REQUIRED_PYTHON_MINOR_VERSION := 9
PYTHON_EXECUTABLE := python$(REQUIRED_PYTHON_MAJOR_VERSION)

# Repository versions
SRC_VERSION := $(shell git describe --tags --match 'v[0-9]*')
SRC_VERSION_TAG_ONLY := $(shell git describe --tags --abbrev=0 --match 'v[0-9]*')

# ADF Related URLs
SRC_URL_BASE := https://github.com/awslabs/aws-deployment-framework
RAW_URL_BASE := https://raw.githubusercontent.com/awslabs/aws-deployment-framework

UPDATE_URL := $(RAW_URL_BASE)/$(UPDATE_VERSION)/Makefile
SRC_TAGGED_URL_BASE := $(SRC_URL_BASE)/tree/$(SRC_VERSION_TAG_ONLY)
MAKE_TAGGED_URL_BASE := $(SRC_URL_BASE)/tree/make/$(MAKEFILE_VERSION)
SRC_TAGGED_INSTALLATION_DOCS_URL := $(SRC_TAGGED_URL_BASE)/docs/installation-guide.md
MAKE_TAGGED_INSTALLATION_DOCS_URL := $(MAKE_TAGGED_URL_BASE)/docs/installation-guide.md
ISSUES_URL := $(SRC_URL_BASE)/issues
RELEASE_NOTES_URL := $(SRC_URL_BASE)/releases/tag/$(SRC_VERSION_TAG_ONLY)

# Command line colors
CLR_RED := $(shell printf "\033[0;31m")
CLR_GREEN := $(shell printf "\033[0;32m")
CLR_YELLOW := $(shell printf "\033[0;33m")
CLR_BLUE := $(shell printf "\033[0;34m")
CLR_END := $(shell printf "\033[0m")

# Files to work with
SAM_VERSIONED_TEMPLATE := ./src/template-sam.yml
SAM_CONFIG_FILE := samconfig.toml
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
.PHONY: build_debs deps src_deps tox docker version_number git_ignore docs
.PHONY: verify_rooling verify_version
.PHONY: pre_build pre_deps_build sam_build post_build build deps_build
.PHONY: pre_deploy_msg pre_deploy sam_deploy post_deploy_msg post_deploy deploy

.venv: .venv/is_ready

.venv/is_ready:
	( \
		test -d .venv || $(PYTHON_EXECUTABLE) -m venv .venv; \
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

report_versions: .venv report_makefile_version
	@echo "$(CLR_YELLOW)*** Beginning of ADF Version Report ***$(CLR_END)"
	@echo "ADF Source version: $(SRC_VERSION)"
	@echo "ADF $$(cat src/template.yml | grep SemanticVersion | xargs)"
	@echo ""
	@( \
		uname --hardware-platform &> /dev/null && ( \
			echo "Hardware platform: $$(uname --hardware-platform 2> /dev/null || echo 'n/a')" && \
			echo "Kernel name: $$(uname --kernel-name 2> /dev/null || echo 'n/a')" && \
			echo "Kernel release: $$(uname --kernel-release 2> /dev/null || echo 'n/a')" \
		) || ( \
			echo "Hardware platform: $$(uname -m 2> /dev/null || echo 'n/a')" && \
			echo "Kernel name: $$(uname -s 2> /dev/null || echo 'n/a')" && \
			echo "Kernel release: $$(uname -r 2> /dev/null || echo 'n/a')" \
		) || exit 0; \
	)
	@echo ""
	@test -e /etc/os-release && echo "OS Release:" && cat /etc/os-release || exit 0
	@echo ""
	@echo "Disk:"
	@df -h $$PWD 2> /dev/null || echo 'N/A'
	@echo ""
	@echo "Dependencies:"
	@echo "docker: $$(docker --version 2> /dev/null || echo '$(CLR_RED)Not installed!$(CLR_END)')"
	@echo "git: $$(git --version 2> /dev/null || echo '$(CLR_RED)Not installed!$(CLR_END)')"
	@echo "sed: $$(sed --version 2> /dev/null || echo 'test' | sed 's/test/works/g' || echo '$(CLR_RED)Not installed!$(CLR_END)')"
	@echo "make: $$(make --version 2> /dev/null || echo '$(CLR_RED)Not installed!$(CLR_END)')"
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
		pip install aws-sam-cli yq packaging; \
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
	( \
		RUNNING_ON_ARCH=$$(arch); \
		if [ "$$RUNNING_ON_ARCH" = "x86_64" ] || [ "$$RUNNING_ON_ARCH" = "i386" ]; then \
			echo "Prepare docker to support the required architectures..." && \
			docker run --rm --privileged multiarch/qemu-user-static --reset -p yes; \
		fi \
	)

version_number: .venv
	@echo "Generate a new version number..."
	( \
		. .venv/bin/activate; \
		BASE_ADF_VERSION=$$(cat $(SRC_DIR)/template.yml | yq '.Metadata."AWS::ServerlessRepo::Application".SemanticVersion' -r); \
		COMMIT_ADF_VERSION=$(SRC_VERSION); \
		sed "s/Version: $$BASE_ADF_VERSION/Version: $$COMMIT_ADF_VERSION/g" $(SRC_DIR)/template.yml > $(SAM_VERSIONED_TEMPLATE); \
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
		echo "* $(CLR_BLUE)$(MAKE_TAGGED_INSTALLATION_DOCS_URL)$(CLR_END)" || \
		echo "* $(CLR_BLUE)$(SRC_TAGGED_INSTALLATION_DOCS_URL)$(CLR_END)"; \
	)
	@echo ""
	@echo "* $(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/admin-guide.md$(CLR_END)"
	@echo ""
	@echo "* $(CLR_BLUE)$(SRC_TAGGED_URL_BASE)/docs/user-guide.md$(CLR_END)"
	@echo ""

verify_tooling: .venv
	@( \
		. .venv/bin/activate; \
		$(PYTHON_EXECUTABLE) --version &> /dev/null && \
		( \
			$(PYTHON_EXECUTABLE) -c "import sys, tarfile; sys.exit(sys.version_info < ($(REQUIRED_PYTHON_MAJOR_VERSION), $(REQUIRED_PYTHON_MINOR_VERSION)) or not hasattr(tarfile, 'data_filter'))" || \
			( \
				$(PYTHON_EXECUTABLE) --version && \
				echo '$(CLR_RED)Python is too old or lacks safe tarfile extraction (PEP 706)!$(CLR_END)' && \
				echo '$(CLR_RED)Python v$(REQUIRED_PYTHON_MAJOR_VERSION).$(REQUIRED_PYTHON_MINOR_VERSION)+ including the tarfile data_filter is required.$(CLR_END)' && \
				exit 1 \
			) \
		) || ( \
			echo '$(CLR_RED)Supported Python version is not installed!$(CLR_END)' && \
			exit 1 \
		); \
	)
	@( \
		docker --version &> /dev/null || ( \
			echo '$(CLR_RED)Docker is not installed!$(CLR_END)' && \
			exit 1 \
		); \
	)
	@( \
		git --version &> /dev/null || ( \
			echo '$(CLR_RED)Git is not installed!$(CLR_END)' && \
			exit 1 \
		); \
	)
	@( \
		sed --version &> /dev/null || echo 'test' | sed 's/test/works/g' &> /dev/null || ( \
			echo '$(CLR_RED)Sed is not installed!$(CLR_END)' && \
			exit 1 \
		); \
	)
	@( \
		jq --version &> /dev/null || ( \
			echo '$(CLR_RED)Jq is not installed!$(CLR_END)' && \
			exit 1 \
		); \
	)

verify_version: .venv
	@# If the version is empty and we are not in a CI build
	@( \
		if [ "Z${SRC_VERSION}" = "Z" ] && [ "Z$${CI_BUILD}" = "Z" ]; then \
			echo '' && \
			echo '$(CLR_RED)Error: Unable to determine the ADF version!$(CLR_END)' && \
			if [ -e .git ]; then \
				echo '$(CLR_RED)The current directory is not a git clone of ADF.$(CLR_END)' && \
				echo '' && \
				echo '$(CLR_RED)Please read the installation guide to resolve this error:$(CLR_END)' && \
				echo '* $(CLR_BLUE)$(MAKE_TAGGED_INSTALLATION_DOCS_URL)$(CLR_END)' && \
				exit 1; \
			fi && \
			echo '$(CLR_RED)Most likely, the git tags have not been fetched yet.$(CLR_END)' && \
			echo '' && \
			echo '$(CLR_RED)Please fetch the git tags from the cloned repository to continue.$(CLR_END)' && \
			echo '$(CLR_RED)You can do this by running:$(CLR_END) git fetch --tags origin' && \
			echo '' && \
			exit 1; \
		fi \
	)
	@# If the src/template.yml version is newer than the git tagged version and
	@# we are not in a CI build
	@( \
		. .venv/bin/activate; \
		BASE_ADF_VERSION=$$(cat $(SRC_DIR)/template.yml | yq '.Metadata."AWS::ServerlessRepo::Application".SemanticVersion' -r); \
		[ "Z$${CI_BUILD}" != "Z" ] || \
		$(PYTHON_EXECUTABLE) -c "import sys; from packaging import version; version.parse(\"$$BASE_ADF_VERSION\") > version.parse(\"$(SRC_VERSION_TAG_ONLY)\") and sys.exit(1)" || \
		( \
			echo '' && \
			echo '$(CLR_RED)Error: ADF Main template version is newer than the requested git tag version!$(CLR_END)' && \
			echo '$(CLR_RED)Most likely, the git tags have not been fetched recently yet.$(CLR_END)' && \
			echo '' && \
			echo '$(CLR_RED)Please fetch the git tags from the cloned repository to continue.$(CLR_END)' && \
			echo '$(CLR_RED)You can do this by running:$(CLR_END) git fetch --tags origin' && \
			echo '' && \
			echo "$(CLR_RED)ADF Main template version (src/template.yml):$(CLR_END) v$$BASE_ADF_VERSION" && \
			echo '$(CLR_RED)Resolved ADF version using git tags:$(CLR_END) $(SRC_VERSION_TAG_ONLY)' && \
			echo '' && \
			exit 1 \
		) \
	)
	@# If there are uncommitted changes or new files, this implies that ADF
	@# might be modified, hence we should track that in the version number
	@( \
		git diff-index --quiet HEAD -- src || ( \
			echo '' && \
			echo '$(CLR_RED)Error: There are uncommitted changes!$(CLR_END)' && \
			echo '$(CLR_RED)Please commit these changes first to continue.$(CLR_END)' && \
			echo '' && \
			exit 1 \
		); \
	)
	@( \
		test -z "$$(git ls-files --others --exclude-standard -- src)" || ( \
			echo '' && \
			echo '$(CLR_RED)Error: New files were added to ADF its source code!$(CLR_END)' && \
			echo '$(CLR_RED)Please commit these changes first to continue.$(CLR_END)' && \
			echo '' && \
			exit 1 \
		); \
	)
	@# If the version number is not a release-tagged version and we are not in a CI build
	@( \
		if [ "Z$(SRC_VERSION)" != "Z$(SRC_VERSION_TAG_ONLY)" ] && [ "Z$${CI_BUILD}" = "Z" ]; then \
			echo '' && \
			echo '$(CLR_RED)Caution: You are about to build the AWS Deployment Framework (ADF)$(CLR_END)' && \
			echo '$(CLR_RED)with commits that have not undergone the standard release testing process.$(CLR_END)' && \
			echo '' && \
			echo '$(CLR_RED)These untested commits may potentially cause issues or disruptions to your$(CLR_END)' && \
			echo '$(CLR_RED)existing ADF installation and deployment pipelines.$(CLR_END)' && \
			echo '$(CLR_RED)Please proceed with extreme caution and ensure you have appropriate backups$(CLR_END)' && \
			echo '$(CLR_RED)and contingency plans in place. It is highly recommended to thoroughly review$(CLR_END)' && \
			echo '$(CLR_RED)and test these commits in a non-production environment before you proceed.$(CLR_END)' && \
			echo '' && \
			echo 'ADF version base tag: $(CLR_RED)$(SRC_VERSION_TAG_ONLY)$(CLR_END)' && \
			echo 'ADF version of current commit: $(CLR_RED)$(SRC_VERSION)$(CLR_END)' && \
			echo '' && \
			echo 'Are you sure you want to continue? [y/N] ' && \
			read answer && \
			if [ "$${answer:-'N'}" != "Y" ] && [ "$${answer:-'N'}" != "y" ]; then \
				echo 'Aborting...' && \
				exit 1; \
			fi \
		fi \
	)

pre_build: build_deps docker version_number verify_version git_ignore

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
	@echo ""
	@echo "$(CLR_GREEN)============================================================$(CLR_END)"
	@echo "$(CLR_GREEN)ADF built successfully!$(CLR_END)"
	@echo "$(CLR_GREEN)============================================================$(CLR_END)"
	@echo ""
	@echo "$(CLR_YELLOW)You can safely ignore the AWS SAM CLI output shown above,$(CLR_END)"
	@echo "$(CLR_YELLOW)including its list of suggested next commands.$(CLR_END)"
	@echo "$(CLR_YELLOW)There is no need to run any of those sam commands$(CLR_END)"
	@echo "$(CLR_YELLOW)(sam validate, sam local invoke, sam sync, or sam deploy).$(CLR_END)"
	@echo ""
	@echo "$(CLR_GREEN)Next step:$(CLR_END) run '$(CLR_BLUE)make deploy$(CLR_END)' to deploy ADF."
	@echo ""
	@echo "$(CLR_YELLOW)Before running 'make deploy', make sure that you have:$(CLR_END)"
	@echo "  * AWS credentials configured for the AWS Organizations"
	@echo "    management account, and"
	@echo "  * permissions to deploy the ADF CloudFormation stack in the"
	@echo "    $(CLR_BLUE)us-east-1$(CLR_END) region of that management account."
	@echo ""
	@echo "$(CLR_YELLOW)If this is your first ADF installation, also confirm that:$(CLR_END)"
	@echo "  * AWS CloudTrail is enabled and spans all regions, and"
	@echo "  * trusted access for AWS Account Management is enabled in AWS"
	@echo "    Organizations (otherwise account bootstrapping will fail)."
	@echo ""

build: verify_tooling pre_build sam_build post_build

deps_build: pre_deps_build sam_build post_build

pre_deploy_msg:
	@echo ""
	@echo ""
	@echo "$(CLR_GREEN)Thank you for deploying ADF, we are about to proceed$(CLR_END)"
	@echo ""
	@echo "$(CLR_RED)Caution:$(CLR_END) You are about to deploy ADF $(SRC_VERSION)."
	@echo "Proceeding with the deployment will directly impact an existing ADF"
	@echo "installation and ADF pipelines in this AWS Organization."
	@echo "It is highly recommended to thoroughly review and test this version"
	@echo "of ADF in a non-production environment before you proceed."
	@echo ""
	@echo "It is important to check the release notes prior to installing or updating."
	@( \
		if [ "Z$(SRC_VERSION)" != "Z$(SRC_VERSION_TAG_ONLY)" ]; then \
			echo "Please read the local CHANGELOG.md file in the root of the repository."; \
		else \
			echo "Release notes of $(SRC_VERSION_TAG_ONLY) can be found at: $(CLR_BLUE)$(RELEASE_NOTES_URL)$(CLR_END)"; \
		fi \
	)
	@echo ""
	@echo "Please also check whether there are known issues at: $(CLR_BLUE)$(ISSUES_URL)$(CLR_END)"
	@echo "If you run into an issue, you can report these via GitHub issues."
	@echo ""
	@echo "$(CLR_YELLOW)In the next step, a few questions need to be answered.$(CLR_END)"
	@echo "$(CLR_YELLOW)Please use the following guide to answer these:$(CLR_END)"
	@echo ""
	@( \
		echo "$(SRC_VERSION_TAG_ONLY)" | grep -E 'v[0-3]\.' &> /dev/null && \
		echo "$(CLR_BLUE)$(MAKE_TAGGED_INSTALLATION_DOCS_URL)$(CLR_END)" || \
		echo "$(CLR_BLUE)$(SRC_TAGGED_INSTALLATION_DOCS_URL)$(CLR_END)"; \
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

# The sed extractions below are covered by
# tests/makefile/samconfig-portability/ - run those tests if you change them.
post_deploy_msg:
	@echo ""
	@echo ""
	@echo "$(CLR_GREEN)============================================================$(CLR_END)"
	@echo "$(CLR_GREEN)ADF is being deployed to your management account!$(CLR_END)"
	@echo "$(CLR_GREEN)============================================================$(CLR_END)"
	@echo ""
	@echo "$(CLR_YELLOW)You can safely ignore any AWS SAM CLI suggestions above.$(CLR_END)"
	@echo ""
	@echo "Most of the remaining work runs automatically. Follow along in"
	@echo "the AWS Console using the steps and links below."
	@echo ""
	@echo "$(CLR_GREEN)What to do next:$(CLR_END)"
	@echo ""
	@( \
		STACK_NAME="$$(sed -nE 's/^[[:space:]]*stack_name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$(SAM_CONFIG_FILE)" 2>/dev/null | head -n 1)"; \
		DEPLOY_REGION="$$(sed -nE 's/^[[:space:]]*region[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$(SAM_CONFIG_FILE)" 2>/dev/null | head -n 1)"; \
		MAIN_REGION="$$(sed -nE 's/.*DeploymentAccountMainRegion=\\?"?([a-z0-9-]+).*/\1/p' "$(SAM_CONFIG_FILE)" 2>/dev/null | head -n 1)"; \
		[ -z "$$STACK_NAME" ] && STACK_NAME="serverlessrepo-aws-deployment-framework"; \
		[ -z "$$DEPLOY_REGION" ] && DEPLOY_REGION="us-east-1"; \
		[ -z "$$MAIN_REGION" ] && MAIN_REGION="YOUR_MAIN_REGION"; \
		echo "$(CLR_YELLOW)1.$(CLR_END) Wait for the $$STACK_NAME stack to reach"; \
		echo "   CREATE_COMPLETE / UPDATE_COMPLETE in CloudFormation, in the"; \
		echo "   $(CLR_BLUE)$$DEPLOY_REGION$(CLR_END) region of the management account:"; \
		echo "     https://console.aws.amazon.com/cloudformation/home?region=$$DEPLOY_REGION#/stacks?filteringStatus=active&filteringText=$$STACK_NAME&viewNested=true&hideStacks=false"; \
		echo ""; \
		echo "$(CLR_YELLOW)2a. Updating an existing install:$(CLR_END) review and merge the pull"; \
		echo "   request ADF opens against the default branch of the"; \
		echo "   aws-deployment-framework-bootstrap CodeCommit repository."; \
		echo "   Merging it starts the bootstrap pipeline"; \
		echo "   ($(CLR_BLUE)$$DEPLOY_REGION$(CLR_END), management account):"; \
		echo "     https://console.aws.amazon.com/codesuite/codecommit/repositories/aws-deployment-framework-bootstrap/pull-requests?region=$$DEPLOY_REGION&status=OPEN"; \
		echo ""; \
		echo "   Once merged, continue with step 2b below."; \
		echo ""; \
		echo "   (A first-time install has no pull request to merge: ADF makes"; \
		echo "   the initial commit to that repository itself, which starts the"; \
		echo "   pipeline. Continue with step 2b below.)"; \
		echo ""; \
		echo "$(CLR_YELLOW)2b. First-time install, and updates after merging:$(CLR_END) watch the"; \
		echo "   bootstrap pipeline in CodePipeline ($(CLR_BLUE)$$DEPLOY_REGION$(CLR_END), management"; \
		echo "   account). If the first run fails to fetch the source, use"; \
		echo "   'Retry' on the failed action:"; \
		echo "     https://console.aws.amazon.com/codesuite/codepipeline/pipelines/aws-deployment-framework-bootstrap-pipeline/view?region=$$DEPLOY_REGION"; \
		echo ""; \
		echo "$(CLR_YELLOW)3.$(CLR_END) Follow the account state machines in AWS Step Functions"; \
		echo "   ($(CLR_BLUE)$$DEPLOY_REGION$(CLR_END), management account) - check recent executions"; \
		echo "   of AccountManagementStateMachine and"; \
		echo "   AccountBootstrappingStateMachine:"; \
		echo "     https://$$DEPLOY_REGION.console.aws.amazon.com/states/home?region=$$DEPLOY_REGION#/statemachines"; \
		echo ""; \
		if [ "$$MAIN_REGION" = "YOUR_MAIN_REGION" ]; then \
			echo "$(CLR_YELLOW)4.$(CLR_END) Once the deployment account is bootstrapped, switch to it in"; \
			echo "   your main region. Replace $(CLR_BLUE)YOUR_MAIN_REGION$(CLR_END) in the links"; \
			echo "   below with that region (for example eu-west-1)."; \
		else \
			echo "$(CLR_YELLOW)4.$(CLR_END) Once the deployment account is bootstrapped, switch to it in"; \
			echo "   your main region ($(CLR_BLUE)$$MAIN_REGION$(CLR_END))."; \
		fi; \
		echo ""; \
		echo "   The aws-deployment-framework-pipelines pipeline generates your"; \
		echo "   pipelines. Watch it in CodePipeline:"; \
		echo "     https://$$MAIN_REGION.console.aws.amazon.com/codesuite/codepipeline/pipelines/aws-deployment-framework-pipelines/view?region=$$MAIN_REGION"; \
		echo ""; \
		echo "   The pipeline generation runs in AWS Step Functions - check the"; \
		echo "   adf-pipeline-management state machine:"; \
		echo "     https://$$MAIN_REGION.console.aws.amazon.com/states/home?region=$$MAIN_REGION#/statemachines"; \
		echo ""; \
		echo "   The aws-deployment-framework-pipelines CodeCommit repository in"; \
		echo "   that region holds the deployment map(s) for your pipelines."; \
	)
	@echo ""
	@echo "For the full walk-through, see the 'What happens next?' section of"
	@echo "the installation guide (and the admin guide when updating) below."
	@echo ""

post_deploy: post_deploy_msg docs

deploy: pre_deploy sam_deploy post_deploy
