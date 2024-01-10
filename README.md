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

Launch ADF via the
[Serverless Application Repository](https://console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:us-east-1:112893979820:applications/aws-deployment-framework)
within the AWS Console.

## Enabling ADF for GovCloud and China Regions

To deploy ADF in GovCloud or China regions, follow these steps:

### GovCloud

1. Launch the ADF installation from an account with a base region on GovCloud (us-gov-west-1).
2. Update your AWS CLI configuration to use the AWS GovCloud endpoint.

### China

1. Launch the ADF installation from an account with a base region on China (cn-north-1).
2. Update your AWS CLI configuration to use the AWS China endpoint.

### Considerations
Be mindful that AWS Products and Services available may differ from the Global partition
Ensure that you follow the specific guidelines and compliance requirements for deploying in GovCloud and China regions.

- Refer to the [Installation Guide](docs/installation-guide.md) for
  Installation steps.
- Refer to the [User Guide](docs/user-guide.md) for using ADF once it is setup.
- Refer to the [Samples Guide](docs/samples-guide.md) for a detailed walk
  through of the provided samples.
