# Multi-Organization ADF Setup Guide

This document describes how ADF can be run and managed in a multi AWS organization
setup.

- [Intended Audience](#intended-audience)
- [Definition of a Multi-Organization ADF Setup](#definition-of-a-multi-organization-adf-setup)
- [Common Use Case for a Multi-Organization ADF Setup - A Multi-Stage Landing Zone](#common-use-case-for-a-multi-organization-adf-setup---a-multi-stage-landing-zone)
- [Propagating Code Changes Between ADF Installations](#propagating-code-changes-between-adf-installations)
- [Best Practices for Multi-Organization ADF setups](#best-practices-for-multi-organization-adf-setups)
  - [1. Create a dedicated adfconfig.yml Per AWS Organization](#1-create-a-dedicated-adfconfigyml-per-aws-organization)
  - [2. Customize the ADF Config File Per AWS Organization](#2-customize-the-adf-config-file-per-aws-organization)
  - [3. Design Multi-Organization ADF Deployment Maps](#3-design-multi-organization-adf-deployment-maps)
  - [4. Make AWS Organization Stage Context Available in AWS CodePipeline Build jobs](#4-make-aws-organization-stage-context-available-in-aws-codepipeline-build-jobs)
  - [5. Customize the Base IAM Roles Per AWS Organization](#5-customize-the-base-iam-roles-per-aws-organization)

## Intended Audience

This guide is intended for users that run a large scale AWS Organization with
complex ADF application deployments and large numbers of ADF deployment pipelines.
Enterprises usually best meet the criteria for a multi AWS organization setup.
We therefore refer to "Enterprises" as the target audience in the section below.
However, the approach described here should be applied to smaller organizations
as well; assuming that sufficient engineering staff is available to support a
multi AWS organization setup.

## Definition of a Multi-Organization ADF Setup

A multi-organization AWS-Deployment-Framework (ADF) setup describes a scenario
where an enterprise (or any user) maintains more than one AWS Organizations. Where
each AWS Organization holds its own dedicated ADF installation.

The following diagram shows such a setup in the most generic level:

![Multi Org Intro](images/aws-multi-org-1.png)

## Common Use Case for a Multi-Organization ADF Setup - A Multi-Stage Landing Zone

The most common use case for a multi-organization ADF setup is a multi-stage
(and multi-organization) [landing zone](https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-aws-environment/understanding-landing-zones.html).
Such a setup enables stable landing zone feature development that is otherwise
not possible in a single AWS Organization.

Let's assume that "Enterprise A" has a dedicated production (referenced as "prod"
hereafter) AWS Organization. This "prod" AWS Organization is used by it's end users
to run all their workloads. In a single AWS Organization setup, the "prod" AWS
Organization is the only AWS Organization that exists. Applying changes to this
single organization, for example updating ADF, changing SCPs or applying enforcing
controls via AWS Config, introduces the risk or disrupting your production workloads.
To mitigate this risk, it is recommended to apply the multi-organization ADF setup
as described in this document.

As part of the multi-organization ADF setup, one or more AWS Organizations are added.
In the instructions below, a separate development ("dev") and integration ("int")
AWS Organization are added. The following diagram shows such an architecture:
![Multi Org Intro](images/aws-multi-org-2.png)

The development flow is as follows:

1. Development work for any landing zone feature always starts in the "dev"
AWS Organization. The ADF repository `aws-deployment-framework-bootstrap` and
`aws-deployment-framework-pipelines` are also considered a landing zone feature.
The "dev" AWS Organization is exclusively reserved for the landing zone
development team. End-users do not have access to the "dev" AWS Organization.
2. Once the code under development is stable and underwent successful unit and
basic integration tests, it is moved from the "dev" AWS Organization to the
"int" AWS Organization. The process of propagating code from one AWS Organization
to another is described in the
[Propagating Code Changes Between ADF Installations section](#propagating-code-changes-between-adf-installations).
3. The "int" AWS Organization is used for final integration testing and
verification. The "int" AWS Organization is exclusively reserved for the landing
zone development team. End-users do not have access to the "int" AWS Organization.
4. Once all tests passed successfully, the code is moved from the "int" AWS
Organization to the "prod" AWS Organization.
5. Assuming that the propagation and the deployment in the "prod"
AWS Organization was successful, the code is now fully deployed in the
"prod" AWS Organization and is available to the end-users.

The benefits of such a setup is that an Enterprise can apply the same common
`Software Development Lifecycle` to typical "one-off" landing zone services that
are hard to test in a single-organization setup. It provides the enterprise's
'Cloud Center of Excellence' (landing zone team) a controlled process to
develop, test, and validate changes to wide reaching mission-critical
services, including but not limited to:

- Service Control Policies changes.
- Identity Center and IAM based Access Management Configuration changes.
- AWS Deployment Framework changes.
- AWS Organization changes; including OU structure.
- Control Tower and Account Provisioning configurations changes.
- Centralized security service configuration changes.
- Centralized cost management configuration changes.
- Centralized networking changes.

The following sections are written in the context of the above described use
case; a multi-stage landing zone.

## Propagating Code Changes Between ADF Installations

With multiple ADF configurations across multiple AWS Organizations there comes a
new challenge to maintain repositories and its configurations across multiple environments.
This applies to the following repositories:

- aws-deployment-framework-bootstrap
- aws-deployment-framework-pipelines
- any other landing zone repository

As the requirements of the bootstrapped resources and ADF configuration evolves
they need to be updated over time. These changes must propagate from one environment
to the next in a coordinated, controlled fashion.

With an `Environment Branching` approach it is possible to build a 'hands-off'
automated mechanism to promote from a "dev" AWS Organization environment to a
"prod" AWS Organization environment. This means that, for example merging code
from the "dev" branch of a repository to the "int" branch of a repository, it
will trigger the deployment process in the "int" AWS Organization.

Implementing such an approach is out of scope for this guide as it heavily
depends on the specific source code and CI/CD tool in use.

## Best Practices for Multi-Organization ADF setups

If you want to run ADF in a multi-organization setup, there are various best
practices that should be followed. When following these recommendations, the
content of the repository `aws-deployment-framework-bootstrap` and
`aws-deployment-framework-pipelines` should be stage agnostic. This means that
you can copy and paste the content of any of those two repositories into any
AWS Organization stage ("dev", "int", "prod") and ADF will behave exactly the same.

### 1. Create a dedicated adfconfig.yml Per AWS Organization

One challenge with synchronizing the `aws-deployment-framework-bootstrap` repository
across AWS Organizations is that the contents of the `adfconfig.yml` configuration
file is typically tailored to the ADF installation. The can be solved by adding a
custom adfconfig file for the given organization.

Adding a configuration file with the name pattern `adfconfig.{organization id}.yml``
in the root of the`aws-deployment-framework-bootstrap` repository will take
precedence over the default `adfconfig.yml` settings file for that organization.

For each AWS organization used in the ADF setup an additional adfconfig
file can be defined.

The following screenshot shows the ADF root directory of a multi-organization ADF
setup with three stages ("dev", "int", "prod"). Each AWS Organization has its own
ADF config file with environment-specific values.
![adf-multi-org-root-directory-screenshot](images/aws-multi-org-adf-config-multi-organization.png)

## 2. Customize the ADF Config File Per AWS Organization

Once a dedicated ADF config file per environment is setup, it needs to be customized
for each AWS Organizations context. It is recommended to make use of the following
ADF configuration options in a multi-organization context:

```yaml
  scm:
    # This setting ensures, that the "prod" branch is selected as the source
    # branch for any ADF deployment pipeline.
    default-scm-branch: prod
    # This setting ensure that the AWS Account 123456789012 is selected as the
    # default AWS account to.
    default-scm-codecommit-account-id: "123456789012"
  org:
    # This setting will create the SSM parameter "/adf/org/stage" in the ADF
    # deployment AWS Account. This parameter then can be referenced as an
    # environment variable in application buildspec files to establish the
    # AWS organization context.
    stage: prod
  deployment-maps:
    # It is recommended to set this setting to "True". When this setting is set
    # to "True", temporary empty OUs are just ignored and do not lead to an error.
    allow-empty: "True"
```

The following sample ADF config file `adfconfig.o-a123456789.yml` shows a
complete example for a "prod" AWS organization.

```yaml
# The following configuration is only loaded for prod Organization:  o-a123456789
roles:
  cross-account-access: AWSControlTowerExecution
  # ^ The role by ADF to assume cross account access

regions:
  deployment-account: eu-central-1
  # ^ The region you define as your main deployment region
  targets: # A list of regions you wish to bootstrap and also deploy into via pipelines
    - us-east-1
config:
  main-notification-endpoint:
    - type: email
      target: john.doe@example.com
      # ^ Email/Slack channel who receives notifications for the main
      # bootstrapping pipeline
  protected:
    - ou-1234-abcdefgh # OU Lockdown
  moves:
    - name: to-root
      action: safe  # Can be safe or remove-base
  scp:
    keep-default-scp: enabled
    # ^ Determines if the default AWSFullAccess SCP stays attached to all OU's
  scm:
    auto-create-repositories: enabled
    default-scm-branch: prod
    default-scm-codecommit-account-id: "123456789012"
  org:
    stage: prod
  deployment-maps:
    allow-empty: "True" # Defaults to "False". Needs to be "True" or "False"
```

### 3. Design Multi-Organization ADF Deployment Maps

The Deployment Maps for ADF exist in the AWS CodeCommit repository
`aws-deployment-framework-pipelines` within the deployment
account. Some additional multi-organization challenges exist when defining
targets for deployments. As a high-level goal, a deployment map should be setup
in such a way, that it can be copied over from one ADF instance to another without
breaking / requiring any change.

The following considerations should be observed when creating deployment maps for
a multi-organization ADF setup:

1. Create Organization-agnostic deployment maps
    - As a best-practice, deployment maps should be free of any hard-coded AWS
      Account IDs for deployment map targets, unless the deployment is destined
      for a single AWS Organization only.
    - Instead, target AWS Accounts via `Account Names`, `Account Tags` or `OU Paths`.
      This will allow ADF to dynamically generate the respective AWS Account IDs
      for the target list when updating the pipelines.
2. Consider AWS service limits for AWS CodePipeline
    - Review the AWS CodePipeline action limitations. [AWS CodePipeline
      Limits](https://docs.aws.amazon.com/codepipeline/latest/userguide/limits.html))
      are:
      - 1000 AWS CodePipeline per AWS Account per region
      - 500 Actions per AWS CodePipeline
      - 50 Actions per AWS CodePipeline Stage
    - Those limits imply that a single ADF pipeline can target 500 AWS Accounts
      max. This may require you to manually balance the targets across multiple
      deployment pipelines.
    - ADF distributes targets across AWS CodePipeline stages within a deployment
      pipeline, spreading the accounts across multiple stages to workaround the
      AWS CodePipeline actions-per-stage limitation. Deployments may need to be
      manually distributed across multiple deployment pipelines if they target
      hundreds of accounts in an AWS Organization.
    - In a large enterprise setup, the number of targets in a "prod"
      AWS Organization for an AWS CodePipeline stage may be much larger than its
      preceding stages in the "dev" and "int" AWS Organizations.
3. Allow empty deployment map targets
    - With the adfconfig setting `allow-empty-target` ([ADF Admin Guide](admin-guide.md)),
      ADF can be instructed to ignore any target that is not resolvable or empty
      (because no AWS Accounts exists in it). It is suggested to set this setting
      to `enabled`. Even though the OU structure and general setup across the different
      AWS Organization stages is usually identical, the number of created
      AWS Accounts might not be. When this setting is set to `enabled`, temporary
      empty OUs are just ignored and do not lead to an error.
4. The source branch for the application code may be different per AWS Organization
    - The above described custom `adfconfig` configuration allows a different
      default branch to be specified in the path `config.scm.default-scm-branch`
      per AWS Organization.

### 4. Make AWS Organization Stage Context Available in AWS CodePipeline Build jobs

ADF applications often contain environment / AWS Organization stage specific
configuration files. In order to allow AWS CodeBuild to select the proper
configuration context for an application, the environment / AWS Organization stage
context needs to be made available. A simple pattern to solve this problem is the
introduction of the SSM parameter `/adf/org/stage` in the buildspec file of the
application. This SSM parameter will be auto-created by ADF. The following snippet
shows the header of such a `codebuild.yaml` file.

```yaml
env:
  parameter-store:
    ADF_ORG_STAGE: "/adf/org/stage"
# [...]
```

This environment variable can then be used to drive decision/deployment logic
within any of the subsequent build commands/actions.

Some scenarios which could require organization specific context include:

- Deriving the default log level based on the organization stage for
a specific CDK application
- Appending the Stage name to AWS resource names having a requirement to be
  both deterministic as well as globally unique
(whilst being deployed into multiple organizations).
- Selecting a config file from a config folder with the following files:
  - `config-dev.yaml`
  - `config-int.yaml`
  - `config-prod.yaml`
- Copy a specific `params` folder to use for the given organization context,
  before `generate_params.py` is invoked:
  `cp -r ./org_specific/${ADF_ORG_STAGE}/params ./params`

### 5. Customize the Base IAM Roles Per AWS Organization

ADF Supports Bootstrapping Baseline CloudFormation Stacks to all AWS Accounts
when they first join an AWS Organization and centrally governing the subsequent
lifecycle of those stacks. [More information on bootstrapping accounts can be
found in the admin guide](admin-guide.md#bootstrapping-accounts).

These Baseline Templates are typically used for setting up the default IAM
roles and Policies necessary for the foundations of an ADF Based Enterprise
Landing Zone.

In guidance with AWS Security Guidelines and `Least Privilege Access Principles`,
it is recommended to reduce the scope of any IAM Policy to the minimum required
Actions, Principals and Resource Scope necessary.

To customize the scope of which resources or principals are permitted within the
IAM Policies of the baseline templates CFN Mapping fields can be utilized based
on the `Org Stage` SSM Parameter. As shown below:

```yaml
Parameters:
  OrgStage:
    Type: "AWS::SSM::Parameter::Value<String>"
    Description: Org Stage
    Default: /adf/org/stage
# At the time this Stack is deployed, the FinOps Account ID SSM Parameter doesn't
# exist, so we derive it from mapping it to the org stage
Mappings:
  # Usage: !FindInMap [OrgStageBasedPropertyMap, !Ref OrgStage, FinOpsAccountId]
  OrgStageBasedPropertyMap:
    dev:
      FinOpsAccountId: 111111111111 # Dev Org
    int:
      FinOpsAccountId: 222222222222 # Int Org
    prod:
      FinOpsAccountId: 333333333333 # Prod Org
```

In the above usage example you can see how the CloudFormation function FindInMap
`!FindInMap [OrgStageBasedPropertyMap, !Ref OrgStage, FinOpsAccountId]` can be
utilized to dynamically reference a custom 'AccountId' within the template,
enabling the construction of account specific granular Resource and Principal ARNs.
