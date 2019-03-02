# AWS Deployment Framework

## Overview

The AWS Deployment Framework *(ADF)* is an flexible framework to manage, control and deploy resources across multiple AWS accounts and regions within an organization.

ADF allows for staged, parallel, multi-account, cross-region deployments of applications or resources via the structure defined in [AWS Organizations](https://aws.amazon.com/organizations/) while taking advantage of services such as [AWS CodePipeline](https://aws.amazon.com/codepipeline/), [AWS CodeBuild](https://aws.amazon.com/codebuild/) and [AWS CodeCommit](https://aws.amazon.com/codecommit/) to elevate the heavy lifting and management compared to a traditional CI/CD setup.

ADF allows for clearly defined deployment and approval stages which are stored in a centralized deployment map configuration file. It also allows for account based bootstrapping, by which you define an AWS CloudFormation template and assign it to a specific Organization Unit (OU) within AWS Organizations. From there, any account you move into this OU will automatically apply this template as its baseline.

## Pre-Requisites

- [awscli](https://aws.amazon.com/cli/)
- [git](https://git-scm.com/)
- [AWS CloudTrail configured](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html) in the AWS Organizations Master account.

## Quick Start

- Refer to the [Admin Guide](/docs/admin-guide.md) for Installation steps and Administration.
- Refer to the [User Guide](/docs/user-guide.md) for using ADF once it is setup.
- Refer to the [Samples Guide](/docs/samples-guide.md) for a detailed walk through of the provided samples.

### Tenets

- Follow Infrastructure as Code best practices.
- AWS Cloud native services first; if a AWS Cloud native service is available and capable, this should be chosen to avoid server-full overheads.
- Enable Developers to be agile with the creation and consumption of their CI/CD Pipelines across numerous AWS accounts and regions.
