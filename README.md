# AWS Deployment Framework

[![Build Status](https://github.com/awslabs/aws-deployment-framework/workflows/ADF%20CI/badge.svg?branch=master)](https://github.com/awslabs/aws-deployment-framework/actions?query=workflow%3AADF%20CI+branch%3Amaster)

[![MegaLinter](https://github.com/awslabs/aws-deployment-framework/workflows/MegaLinter/badge.svg?branch=master)](https://github.com/awslabs/aws-deployment-framework/actions?query=workflow%3AMegaLinter+branch%3Amaster)

The AWS Deployment Framework *(ADF)* is an extensive and flexible framework to
manage and deploy resources across multiple AWS accounts and regions within an
AWS Organization.

ADF allows for staged, parallel, multi-account, cross-region deployments of
applications or resources via the structure defined in
[AWS Organizations](https://aws.amazon.com/organizations/) while taking
advantage of services such as
[AWS CodePipeline](https://aws.amazon.com/codepipeline/),
[AWS CodeBuild](https://aws.amazon.com/codebuild/), and
[AWS CodeCommit](https://aws.amazon.com/codecommit/) to alleviate the
heavy lifting and management compared to a traditional CI/CD setup.

ADF allows for clearly defined deployment and approval stages which are stored
in a centralized configuration file. It also allows for account based
bootstrapping, by which you define an
[AWS CloudFormation](https://aws.amazon.com/cloudformation/) template and
assign it to a specific Organization Unit (OU) within AWS Organizations.
From there, any account you move into this OU will automatically apply this
template as its baseline.

## Quick Start

- Refer to the [Installation Guide](docs/installation-guide.md) for
  Installation steps.
- Refer to the [Admin Guide](docs/admin-guide.md) on guidance how-to manage and
  administrate ADF.
- Refer to the [User Guide](docs/user-guide.md) for using ADF to generate
  and manage pipelines.
- Refer to the [Technical Guide](docs/technical-guide.md) if you want to learn
  more about the inner workings of ADF. For example in case you want to
  contribute or build on top of ADF.
- Refer to the [Samples Guide](docs/samples-guide.md) for a detailed walk
  through of the provided samples.
