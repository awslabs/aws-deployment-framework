# AWS Deployment Framework

[![Build Status](https://github.com/awslabs/aws-deployment-framework/workflows/ADF%20CI/badge.svg?branch=master)](https://github.com/awslabs/aws-deployment-framework/actions?query=workflow%3AADF%20CI+branch%3Amaster)

The [AWS Deployment Framework](https://github.com/awslabs/aws-deployment-framework)
*(ADF)* is an extensive and flexible framework to manage and deploy resources
across multiple AWS accounts and regions within an AWS Organization. This
application should be deployed via the SAR in the [Management AWS
account](admin-guide.md#management-account) of your AWS Organization within the
`us-east-1` region. For more information on setting up ADF please see the
[installation
guide](https://github.com/awslabs/aws-deployment-framework/tree/master/docs/installation-guide.md).

- **Application Name:** The stack name of this application created via AWS
  CloudFormation. By default, this should be `aws-deployment-framework`.

- **CrossAccountAccessRoleName:** The name of the IAM Role that ADF will use to
  access other AWS Accounts within your Organization to create and update base
  CloudFormation stacks. This role must exist in all AWS accounts within your
  Organization that you intend to use ADF with. When creating new AWS Accounts
  via AWS Organizations you can define an initial role that is created on the
  account, that role name should be standardized and can be used as this initial
  cross-account access role.

  *This is not required when performing an update between versions of ADF.*

- **DeploymentAccountEmailAddress:** The Email address associated with the
  Deployment Account, If you have an existing account you wish to use as the
  deployment account, insert the email address of the AWS account here.

  *This is not required when performing an update between versions of ADF.*

- **DeploymentAccountId:** The AWS Account number of the **existing** Deployment
  Account, only required if an existing account should be used. A deployment
  account will be created if this value is omitted. Only required if using
  pre-existing AWS Account as the Deployment Account.

  *This is not required when performing an update between versions of ADF.*

- **DeploymentAccountMainRegion:** The AWS region that will centrally hold all
  AWS CodePipeline Pipelines. Pipeline deployments can still span multiple
  regions however they are still stored and viewed from a single region
  perspective. This would be considered your default ADF AWS Region.

  *This is not required when performing an update between versions of ADF.*

- **DeploymentAccountName:** The Name of the centralized Deployment Account. If
  you have an existing account you wish to use as the deployment account, insert
  the name of the AWS account here. *This is not required when performing an
  update between versions of ADF.*

## InitialCommit

These are parameters that relate to the setting up the `adfconfig.yml` file and
its initial commit to the bootstrap repository. The `adfconfig.yml` file defines
base level settings for how ADF operates.

When deploying ADF for the first time, part of the installation process will
automatically create an AWS CodeCommit repository on this AWS Account within the
`us-east-1` region. It will also make the initial commit to the default branch
of this repository with a default set of examples that act as a starting point
to help define the AWS Account bootstrapping processes for your Organization.

When making this initial commit into the repository, these below settings are
passed directly the `adfconfig.yml` file prior to it being committed.

- **DeploymentAccountAlias:** The Alias of the Deployment Account. The account
  alias is a globally unique name for an account that enable things such as
  custom login URLs. Read more
  [here](https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html#AboutAccountAlias)

- **DeploymentAccountTargetRegions:** An optional comma separated list of
  regions that you may want to deploy resources *(Applications, CloudFormation
  etc)* into via AWS CodePipeline, this can always be updated later via the
  `adfconfig.yml` file. **(e.g. `us-west-1`,`eu-west-1`)**.

  *This is not required when performing an update between versions of ADF.*

- **MainNotificationEndpoint:** An optional Email Address that will receive
  notifications in regards to the bootstrapping pipeline on the management
  account.

  *This is not required when performing an update between versions of ADF.*

- **ProtectedOUs:** An optional comma separated list of OU ids that you may want
  to protect against having bootstrap stacks applied **(e.g.
  `ou-123`,`ou-234`)**.

  *This is not required when performing an update between versions of ADF.*

## What happens next?

After hitting **Deploy** the base AWS Deployment Framework
[CloudFormation stack](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks)
will be created.

This Stack contains a few notable resources such as:

- an [AWS CodeCommit
  Repository](https://console.aws.amazon.com/codesuite/codecommit/repositories/aws-deployment-framework-bootstrap/browse?region=us-east-1)
- along with an associated [AWS CodeBuild
  Project](https://console.aws.amazon.com/codesuite/codebuild/projects/aws-deployment-framework-base-templates/history?region=us-east-1)
- and an [AWS CodePipeline
Pipeline](https://console.aws.amazon.com/codesuite/codepipeline/pipelines/aws-deployment-framework-bootstrap-pipeline/view?region=us-east-1)

The CodeCommit Repository will have its first commit made to it automatically by
the ADF installation process. This is a starting point for using ADF and helps
define the bootstrap process for your AWS Ecosystem.

Once the initial commit has been made, CodePipeline will run which kicks off AWS
CodeBuild to sync the content of the repository with Amazon S3.

Once the content is synced, you are ready to bootstrap your Deployment account
by moving it into the deployment OU within AWS Organizations.

Before bootstrapping an AWS Account its important to understand how ADF handles
AWS Account provisioning. Read more about [AWS Account
Provisioning](./admin-guide.md#account-provisioning) in the admin guide.

## Upgrading between versions?

Ensure the **CrossAccountAccessRole** and **Application Name** are the same
value you used for your initial deployment. Click **Deploy**. As part of the
installation phase, a custom CloudFormation resource will make a Pull Request
against the [AWS CodeCommit
Repository](https://console.aws.amazon.com/codesuite/codecommit/repositories/aws-deployment-framework-bootstrap/browse?region=us-east-1)
with the content from the latest release of ADF.

Ensure none of your specific bootstrap templates are being overwritten or
affected in any way before merging. Once merged, the pipeline will run, this
completes the update process.

Upgrading from `*2.x` to `3.x*`? See the
[3.0 release notes](https://github.com/awslabs/aws-deployment-framework/releases)
for details.
