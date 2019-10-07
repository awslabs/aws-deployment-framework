# AWS Deployment Framework

[![Build Status](https://travis-ci.org/awslabs/aws-deployment-framework.svg?branch=master)](https://travis-ci.org/awslabs/aws-deployment-framework)

The [AWS Deployment Framework](https://github.com/awslabs/aws-deployment-framework) *(ADF)* is an extensive and flexible framework to manage and deploy resources across multiple AWS accounts and regions within an AWS Organization. This application should be deployed via the SAR in the master AWS account of your AWS Organization within the **us-east-1** region. For more information on setting up ADF please see the [installation guide](https://github.com/awslabs/aws-deployment-framework/tree/master/docs/installation-guide.md).

## Application settings

#### Application Name
> The stack name of this application created via AWS CloudFormation.

#### CrossAccountAccessRoleName
> The Name of the IAM Role that ADF will use to access other AWS Accounts within your Organization to create and update base CloudFormation stacks. This role must exist in all AWS accounts within your Organization that you intend to use ADF with. When creating new AWS Accounts via AWS Organizations you can define an initial role that is created on the account, that role name should be standardized and can be used as this initial cross account access role. *This is not required when performing an update between versions of adf*

#### DeploymentAccountMainRegion
> The AWS region that will centrally hold all AWS CodePipeline Pipelines. Pipeline deployments can still span multiple regions however they are still stored and viewed from a single region perspective. This would be considered your default ADF AWS Region. *This is not required when performing an update between versions of adf*

#### LogLevel
> General Logging level output for ADF that will be shown in AWS Lambda and AWS CodeBuild Logs output. *This is not required when performing an update between versions of adf*

#### TerminationProtection
> Termination Protection can be passed in to enable Protection for all ADF base stacks. *This is not required when performing an update between versions of adf*

### DeploymentAccount
These Parameters are for the initial setup of the Deployment AWS Account. The Deployment account is a centralized AWS account that holds AWS CodePipeline Pipelines that will deploy resources such as Applications or CloudFormation templates into various other AWS Accounts throughout your Organization. The Deployment Account is responsible for all acts of Deployment throughout the organization and acts as a broker between AWS Accounts that might be used for development or storing specific source code and those AWS accounts that exist to run line of business workloads such as Test, Acceptance and Production accounts.

#### DeploymentAccountEmailAddress
> The Email address associated with the Deployment Account, only required if Deployment Account requires creation. *This is not required when performing an update between versions of adf*

#### DeploymentAccountId
> The AWS Account number of the **existing** Deployment Account, only required if an existing account should be used. A deployment account will be created if this value is omitted. Only required if using pre-existing AWS Account as the Deployment Account. *This is not required when performing an update between versions of adf*

#### DeploymentAccountName
> The Name of the centralized Deployment Account. Only required if Deployment Account requires creation. *This is not required when performing an update between versions of adf*

### InitialCommit
These are parameters that relate to the setting up the *adfconfig.yml* file and its initial commit to the bootstrap repository. The *adfconfig.yml* file defines base level settings for how ADF operates. When deploying ADF for the first time, part of the installation process will automatically create an AWS CodeCommit repository on this AWS Account within the **us-east-1** region. It will also make the initial commit to the master branch of this repository with a default set of examples that act as a starting point to help define the AWS Account bootstrapping processes for your Organization. When making this initial commit into the repository, these below settings are passed directly the *adfconfig.yml* file prior to it being committed.

#### DeploymentAccountTargetRegions
> An optional comma separated list of regions that you may want to deploy resources *(Applications, CloudFormation etc)* into via AWS CodePipeline, this can always be updated later via the adfconfig.yml file. **(eg us-west-1,eu-west-1)**. *This is not required when performing an update between versions of adf*

#### MainNotificationEndpoint
> An optional Email Address that will receive notifications in regards to the bootstrapping pipeline on the master account. *This is not required when performing an update between versions of adf*

#### ProtectedOUs
> An optional comma separated list of OU ids that you may want to protect against having bootstrap stacks applied **(eg ou-123,ou-234)**. *This is not required when performing an update between versions of adf*
