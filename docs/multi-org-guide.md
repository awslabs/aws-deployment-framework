# Multi-Org-Guide

- [Multi Org Guide](#multi-org-guide)
  - [What is A Multi-Org AWS-Deployment-Framework Setup](#what-is-a-multi-org-aws-deployment-framework-setup)
  - [Coordinating Changes Between ADF Installations](#Coordinating-Changes-Between-ADF-Installations)
  - [Customizing ADF Config Per AWS Organization](#customizing-adfconfig.yml-per-aws-organization)
  - [Customizing Base IAM Roles Per Organization](#customizing-base-iam-roles-per-organization)
  - [Customizing Codepipeline BuildSpecs Per Organization](#customizing-codepipeline-buildspecs-per-organization)
  - [Considerations for Multi-Org Deployment Maps](#considerations-for-multi-org-deployment-maps)


# What is A Multi-Org AWS-Deployment-Framework Setup
A Multi-Org AWS-Deployment-Framework (ADF) setup describes a scenario where an 
Enterprise maintains more than one AWS Organizations and each with it's own
dedicated ADF installation.

The benefits of such a configuration is that in Enteprise organizations 
hosting with many production cloud workloads and applications which are deployed 
and governed by ADF, can apply the same common `Software Development Lifecycle` 
approaches to configuration changes in the deployment and governance tooling as
they do with the workloads they run. 

With a dedicated AWS Organization and ADF install setup with Dev, Int and Prod 
Organizations, it enables an Enterprises 'Cloud Center of Excellence' an 
controlled process to validate changes to wide reaching mission-critical 
services, including but not limited to:

- Service Control Policies Updates
- Identity Center and IAM based Access Management Configuration changes
- Deployment Framework Updates
- Control Tower and Account Provisioning Configurations
- Centralized Security Hub and Cost Management Configurations
- Networking Architectural changes.

# Coordinating Changes Between ADF Installations 
With Multiple ADF configurations within a single organization there comes a 
new challenge to maintain ADF-Bootstrap repository configurations across multiple 
environments. Typically in an ADF Installation for any given Organization you 
would define a customized configuration, and bootstrapped Global Roles and or 
resources.

As the requirements of the bootstrapped resources and adf configuration evolve
they need to be updated over time, and these changes ideally propagated from one
 Installation to the next in a coordinated, controlled fashion.

One approach to promoting validated changes in an `ADF Installation` from 
a Dev to Int to Prod Organization could be to mirror specific branches of
a Source ADF Repository to a Target ADF Repository, Consider the Following table

Org | Repository | Branch | Commit Trigger
--|--|--|--
Dev | AWS-deployment-framework-Bootstrap | Dev Branch | Trigger State Machine Dev Org
Dev | AWS-deployment-framework-Bootstrap | Int Branch | Mirror to Int Org
Int | AWS-deployment-framework-Bootstrap | Int Branch | Trigger State Machine Int Org
Int | AWS-deployment-framework-Bootstrap | Prod Branch | Mirror to Prod Org
Prod | AWS-deployment-framework-Bootstrap | Prod Branch | Trigger State Machine Int Org

Here with an `Environment Branching` approach it's possible to build a 'hands-off' 
automated mechanism to Promote from a Dev ADF Installation to a Prod Installation.

# Customizing adfconfig.yml Per AWS Organization
One challenge with synchronising the aws-deployment-framework-bootstrap repository
across AWS Organizations is that the contents of the `adfconfig.yml` configuration
file is typically tailored to the ADF installation. The can be solved by adding a 
custom adfconfig file for the given organization.

Adding a configuration file with the name pattern `adfconfig.{organization id}.yml`
in the root of the `aws-deployment-framework-bootstrap` repository will take
precedence over the default `adfconfig.yml` settings file for that organization.

For each AWS organization used with the ADF Framework setup an additional adfconfig
file can be defined.

# Customizing Base IAM Roles Per Organization
ADF Supports Bootstrapping Baseline Cloudformation Stacks to all accounts
when they first join an AWS Organization and centrally governing the subsequent 
Lifecycle of those Stacks. [See Here](admin-guide.md#bootstrapping-accounts) 

These Baseline Templates are typically used for Setting up Default IAM Roles and
Policies necessary for the foundations of an ADF Based Enteprise Landing Zone. 

In guidance with AWS Security Guidelines and `Least Privilege Access Principles`,
it it recommended to reduce the scope of any IAM Policy to the minimum required
Actions, Principals and Resource Scope necessary. 

To customize the scope of which resources or Principals are permitted within the
IAM Policies of the Baseline templates CFN Mapping fields can be utilized based 
on the `Org Stage` SSM Parameter. As shown below:

```
Parameters:
  OrgStage:
    Type: "AWS::SSM::Parameter::Value<String>"
    Description: Org Stage
    Default: /adf/org/stage
# At the time this Stack is deployed, the FinOps Account ID SSM Parameter doesn't
# exist, so we derive it from mapping it to the org stage
Mappings:
  # Usage:!FindInMap [OrgStageBasedPropertyMap, !Ref OrgStage, FinOpsAccountId]
  OrgStageBasedPropertyMap:
    dev:
      FinOpsAccountId: 1234567891012 # Dev Org 
    int:
      FinOpsAccountId: 1234567891013 # Int Org
    prod:
      FinOpsAccountId: 1234567891014 # Prod Org
```
In the above usage example you can see how the Cloudformation function FindInMap
`!FindInMap [OrgStageBasedPropertyMap, !Ref OrgStage, FinOpsAccountId]` can be
utilized to dynamically reference a custom 'AccountId' within the Template,
enabling the construction account specific granular Resource/Principal ARNS.

# Customizing Codepipeline BuildSpecs Per Organization
A simple pattern to customize the buildspec is to load the `adf/org/stage` parameter
from ssm parameter from the parameter store via codebuild native mechanism.

```
env:
  parameter-store:
    ADF_ORG_STAGE: "/adf/org/stage"
```

This environment variable can then be used to drive decision/deployment logic
within any of the subsequent build commands/actions.
Some scenarios which could require Org specific context:
- Deriving the default log level based on the org stage for
a specific CDK application 
- Appending the Stage name to AWS resource names having a requirement to be 
both deterministic as well as globally unique 
(whilst being deployed into multiple organizatinos)

# Considerations for Multi-Org Deployment Maps
Whilst the Deployment Maps for ADF exist within a simarly named 
`aws-deployment-framwork-pipelines` codecommit repository within the deployment 
account. 

Some additional Multi-Org challenges exist when defining Targets for Deployments.

The following considerations should be observed:
- Avoid utilizing Account Ids for Deployment Map Targets unless the deployment
 is destined for a single organization.
  - As an alternative Deploy via `Account Names`, `Account Tags` or `OU Paths`
   which ADF will then use to dynamically generate the respective Account IDs 
   Target List when updating the Pipelines.
- Consider in a Large Enteprise Setup the number of targets that a Production
stage generates may be much greater than in predecessing Stages and design accordingly 
  - Review the Codepipeline action limitations.
  - ADF handles best efforts to distribute Targets across Stages with a Pipeline, however 
  Deployments may need to be distributed across Multiple Pipelines when upper limits are reached.
- The source branch for the application code may be different per Organization
  - The above described custom `adfconfig` configuration allows a different default 
branch to be specified in the path `config.scm.default-scm-branch` per Organization