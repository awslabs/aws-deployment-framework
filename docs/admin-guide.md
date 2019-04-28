# Administrator Guide

- [Overview](#overview)
- [Pre-Requisites](#pre-requisites)
- [Src Folder](#src-folder)
- [Installation Instructions](#installation-instructions)
- [adfconfig](#adfconfig)
- [Accounts](#accounts)
  - [Master](#master-account)
  - [Deployment](#deployment-account)
  - [Bootstrapping](#bootstrapping-accounts)
    - [Bootstrapping Overview](#bootstrapping-overview)
    - [Bootstrapping Inheritance](#bootstrapping-inheritance)
    - [Regional Bootstrapping](#regional-bootstrapping)
    - [Global Bootstrapping](#global-bootstrapping)
    - [Bootstrapping Regions](#region-bootstrapping)
- [Service Control Policies](#service-control-policies)
- [Pipelines](#pipelines)
  - [Pipeline Parameters](#pipeline-parameters)
  - [Pipeline Types](#pipeline-types)
- [Default Deployment Account Region](#default-deployment-account-region)
- [Integrating Slack](#integrating-slack)
- [Updating Between Versions](#updating-between-versions)

## Overview

### High Level Bootstrapping Process

![bootstrap-process](./images/adf-bootstrap-high-level.png)

### High Level Pipeline Process

![pipeline-process](./images/adf-pipeline-high-level.png)

## Pre-Requisites

- [awscli](https://aws.amazon.com/cli/)
- [git](https://git-scm.com/)
  - [AWS CodeCommit Setup](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html) 
- [AWS CloudTrail configured](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html) in the AWS Organizations Master account.

## Src Folder

The `src` folder contains *three* sub-folders that make up The ADF.

- initial
  > The initial folder is used to initially create the AWS Deployment Framework within your root AWS Account. It creates resources that are used to facilitate the creation and streamline the automation of the following steps.
- bootstrap_repository
  > The bootstrap_repository folder is responsible for defining your bootstrapping AWS CloudFormation templates that will be assigned to AWS Organizations Organizational Units (OUs) and applied to accounts/regions when they are moved into the OU. This should be initialized as its own git repository and will have a remote in the master account. 
- pipelines_repository
  > The pipelines_repository folder is responsible for defining your deployment pipelines in the deployment_map.yml file which allows for stages, regions and variables configurations for pipelines. This should be initialized as its own git repository and will have a remote in the deployment account.

## Installation Instructions

The below instructions are based on the use-case in which you have no resources in any of your AWS accounts. However, The AWS Deployment Framework *(ADF)* can be implemented with pre-existing resources.

1. Ensure you have setup a new [AWS CloudTrail](https://aws.amazon.com/cloudtrail/) *(Not the default trail)* in your Master Account that spans all regions and that you are able to view trail information in the AWS CloudTrail console.

2. Create an [AWS Organization](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_create.html). Make note of your Organization ID which is part of the ARN *(eg o-zx2u19zz64 is the Organization ID in the ARN arn:aws:organizations::99999999999:root/o-zx2u19zz64/r-a3db)*. In Order to use SCP management and automation within ADF the Organization must be created with All Features enabled *(which is default)*.

3. Create a new AWS CloudFormation stack in the Master account from the `bucket.yml` template in the *us-east-1* region. *(BucketName can be whatever you like)*

```bash
aws cloudformation create-stack \
--stack-name aws-deployment-framework-master-bucket \
--template-body file://$PWD/src/initial/bucket.yml \
--parameters ParameterKey=BucketName,ParameterValue=adf-base-s3-bucket-us-east-1 \
--region us-east-1
```

4. Create a new AWS Account that will act as your [Deployment Account](#deployment-account) via [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html). Once created, leave it in the root of your Organization. Create a new AWS CloudFormation stack in the Master account to be used by the Deployment Account and its resources from the `bucket.yml` template. This stack should be passed the Deployment Account Id that was just created as a parameter and should also be created in the region that you have chosen as your [default Deployment Account region](#default-deployment-account-region). *(eu-central-1 used as example below, BucketName can be whatever you like)*

```bash
aws cloudformation create-stack \
--stack-name aws-deployment-framework-deployment-bucket \
--template-body file://$PWD/src/initial/bucket.yml \
--parameters ParameterKey=BucketName,ParameterValue=adf-base-s3-bucket-eu-central-1 \
ParameterKey=DeploymentAccountId,ParameterValue=111111111111 \
--region eu-central-1
```

5. Execute the AWS CloudFormation template **src/initial/template.yml** in the **us-east-1** Region. In the below commands the *MASTER_ACCOUNT_BUCKET_NAME* variable represents the S3 Bucket name you created in the *us-east-1* region in step 3. The *DEPLOYMENT_ACCOUNT_BUCKET_NAME* is the name of the bucket created in step 4 and the *ORGANIZATION_ID* is that from step 2.

```bash
aws cloudformation package \
--template-file $PWD/src/initial/template.yml \
--s3-bucket MASTER_ACCOUNT_BUCKET_NAME \
--output-template-file $PWD/template-deploy.yml \
--region us-east-1

aws cloudformation deploy \
--stack-name aws-deployment-framework-base \
--template-file $PWD/template-deploy.yml \
--capabilities CAPABILITY_NAMED_IAM \
--parameter-overrides DeploymentAccountBucket=DEPLOYMENT_ACCOUNT_BUCKET_NAME \
OrganizationId=ORGANIZATION_ID \
--region us-east-1
```

6. Once the stack has completed, it will of created a [AWS CodeCommit](https://aws.amazon.com/codecommit/) repository **(aws-deployment-framework-bootstrap)** in the master account *(among other resources)*. This repository is used as a entry point for all [bootstrap stacks](#bootstrapping-accounts) and [SCPs](#service-control-policies) throughout your organization. Familiarize yourself with the folder structure of **src/bootstrap_repository**, this folder should be initialized as a [git repository](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) and be arranged to suit your desired [AWS Organization](https://aws.amazon.com/organizations/) structure and desired bootstrapping configuration. The *deployment* and *adf-build* folder are mandatory in the root of this repository, for everything else, please read [bootstrapping accounts](#bootstrapping-accounts). Before continuing to step 7, ensure you have defined your framework configuration in the *adfconfig.yml* file *(you can use example-adfconfig.yml as a starter)*. For more info on *adfconfig.yml* please see the section on [adfconfig](#adfconfig) in this guide.

7. Once you have defined what base templates will be applied to which organizational units you should push the contents of *bootstrap_repository* to the *aws-deployment-framework-bootstrap* repository in *us-east-1*. The change will be picked up and will start the Pipeline *(aws-deployment-framework-bootstrap-pipeline)* which was created in the master account. This pipeline is responsible for syncing the folder structure with Amazon S3. Each time you push to this Repository, AWS CodeBuild will sync the folder structure with S3 and also update any of the bootstrap stacks and SCPs in AWS Accounts throughout your Organization. This allows you to update your templates, push them into CodeCommit which starts Codepipeline and thus CodeBuild to update bootstrap stacks throughout all of your accounts and regions in a way that promotes continuous integration and deployment. Pushing to this Repository also updates any of your configuration in the *adfconfig.yml* with Parameter Store.

8. Once your pipeline has successfully synced the folder structure with Amazon S3. Create an new Organizational Unit in AWS Organizations in the root named **'deployment'**. This OU will hold the AWS Account that is referred to as the *'Deployment Account'* throughout the ADF.

9. Move the Deployment Account that was created in step 4 into the OU called `deployment`. This action will trigger [AWS Step Functions](https://aws.amazon.com/step-functions/) to run and start the bootstrap process for the deployment account. You can view the progress of this in the AWS Step Functions console from the master account in the us-east-1 region.

10. Once the Deployment Account base stack is complete in the regions you defined, you are ready to create further accounts and build out your Organization. Bootstrap further accounts by moving them into the OU that corresponds to their purpose. At this point you can follow the [sample guide](./samples-guide.md) to follow along with the samples included in this repository which will show in detail how pipelines function in ADF. Otherwise, if you just want to get started making pipelines you can create a `deployment_map.yml` file *(see example-deployment_map.yml for a starting point.)* in the *pipelines_repository* folder and define some pipelines that tie together a source and associated targets.

## adfconfig

The `adfconfig.yml` file that resides on the [Master Account](#master-account) and defines the general high level configuration for the AWS Deployment Framework. These values are stored in AWS Systems Manager Parameter Store and are used for certain orchestration options throughout your Organization. Below is an example of its contents.

```yaml
roles:
  cross-account-access: OrganizationAccountAccessRole

regions:
  deployment-account:
    - eu-central-1
  targets:
    - eu-central-1
    - eu-west-1

config:
  main-notification-endpoint:
    - type: email
      target: john@doe.com
  moves:
    - name: to-root
      action: safe
  protected:
    - ou-123
  scp:
    keep-default-scp: enabled
```

In the above example we have three main properties in `roles`, `regions` and `config`.

#### Roles

Currently, the only role specification that the *adfconfig.yml* file requires is the role **name** you wish to use for cross account access. The AWS Deployment Framework requires an role that will be used to initiate bootstrapping and allow the [Master Account](#master-account) access to assume access in target accounts to facilitate bootstrapping creation and updating processes. When you create new accounts in your AWS Organization they will all need to be instantiated with a role of this same name. When creating a new account, by default, the role you choose as the [Organization Access role](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html) comes with Administrator Privileges in IAM.

#### Regions
The Regions specification plays an important role in how your Deployment Framework deployment is laid out. You should choose a single `deployment-account` region that you would consider your primary region of choice. You should also define target regions you would like to apply baselines to *and* have as deployment targets for your pipelines. If you decide to add more regions later that is also fine. If you add a new region to this list and push the *aws-deployment-framework-bootstrap* repository to the master account it will apply the bootstrapping process to all of your existing accounts for the new region added. You can **not** have AWS CodePipeline deployment pipelines deploy into regions that are not part of this list of bootstrapped regions. In the above example we want our main region to be the `eu-central-1` region and we also want to have that region as a target for the deployment pipelines along with `eu-west-1`. These are also the two regions we plan to have deployment pipelines deploy resources into.

#### Config

Config has three components in `main-notification-endpoint`, `moves` and `protected`.

- **main-notification-endpoint** is the main notification endpoint for the bootstrapping pipeline and deployment account pipeline creation pipeline. This value should be a valid email address or [slack](./admin-guide/#integrating-slack) channel that will receive updates about the status *(Success/Failure)* of CodePipeline that is associated with bootstrapping and creation/updating of all pipelines throughout your organization.
- **moves** is configuration related to moving accounts within your AWS Organization. Currently the only configuration options for `moves` is named *to-root* and allows either `safe` or `remove_base`. If you specify *safe* you are telling the framework that when an AWS Account is moved from whichever OU it currently is in, back into the root of the Organization it will not make any direct changes to the account. It will however update any AWS CodePipeline pipelines that the account belonged to so that it is no longer a valid target. If you specify `remove_base` for this option and move an account to the root of your organization it will attempt to the base CloudFormation stacks *(regional and global)* from the account and then update any associated pipeline.
- **protected** is a configuration that allows you to specify a list of OUs that are not configured by the AWS Deployment Framework bootstrapping process. You can move accounts to the protected OUs which will skip the standard bootstrapping process. This is useful for migrating existing accounts into being managed by The ADF.
- **scp** allows the definition of configuration options that relate to Service Control Policies. Currently the only option for *scp* is *keep-default-scp* which can either be *enabled* or *disabled*. This option determines if the default FullAWSAccess Service Control Policy should stay attached to OUs that are managed by an *scp.json* or if it should be removed to make way for a more specific SCP, by default this is *enabled*. Its important to understand how SCPs work before setting this setting to disabled. Please read [How SCPs work](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_about-scps.html) for more information.

## Accounts

### Master Account

The Master account *(also known as root)* is the owner of the AWS Organization. This account is the only account that is allowed to access AWS Organizations and make changes such as creating accounts or moving accounts the Organization. Because of this, it is important that you keep the account safe and [well structured](https://docs.aws.amazon.com/aws-technical-content/latest/cost-optimization-laying-the-foundation/aws-account-structure.html) when it comes to IAM access and controls. The AWS Deployment Framework does deploy minimal resources into the master account to allow processes such as [bootstrapping](#bootstrapping-accounts) and to take advantage of changes of structure within your AWS Organization. The CodeCommit repository on the Master accounts holds bootstrapping templates and parameters along with the `adfconfig.yml` file which defines how the framework orchestrates certain tasks.

### Deployment Account

The Deployment Account is the gatekeeper for all deployments throughout an Organization. Once the baselines have been applied to your accounts via the bootstrapping process, the Deployment account connects the dots by taking source code and resources from a repository *(Github / CodeCommit)* and into the numerous target accounts and regions as defined in the deployment map. The Deployment account holds the [deployment_map.yml](#deployment_map) file which defines where, what and how your resources will go from their source to their destination. In an Organization there should only be a single Deployment account. This is to promote transparency throughout an organization and to reduce duplication of code and resources. With a single Deployment Account teams can see the status of other teams deployments while still being restricted to making changes to the `deployment_map.yml` via [Pull Requests](https://docs.aws.amazon.com/codecommit/latest/userguide/pull-requests.html) against the pipeline definition repository that resides in the deployment account.

### Bootstrapping Accounts

#### Bootstrapping Overview

The Bootstrapping of AWS an Account is a concept that allows you to specify an AWS CloudFormation template that will automatically be applied any account that is moved into a specific Organizational Unit in AWS Organizations. Bootstrapping of AWS accounts is a convenient way to apply a baseline to an account or sub-set of accounts based on the structure of your AWS Organization.

When creating the base AWS Deployment Framework stack in the master account, a CodeCommit repository titled `aws-deployment-framework-bootstrap` will also be created. This repository acts as an entry point for bootstrapping templates. The definition of which templates are applied to which Organization Unit are defined in the folder structure of the `aws-deployment-framework-bootstrap` repository.

Create a folder structure and associated CloudFormation templates *(global.yml)* or *(regional.yml)* and parameters *(global-params.json)* or *(regional-params.json)* that match your desired specificity when bootstrapping your AWS Accounts. Commit and push this repository to the CodeCommit repository titled `aws-deployment-framework-bootstrap` on the master account. The `regional.yml` is optional however the base configuration required for the `global.yml` for all accounts can be found in the `global.yml` in the base of the *bootstrap_repository* repository.

Pushing to this repository will initiate AWS CodePipeline to run which will in-turn start AWS CodeBuild to sync the contents of the repository with S3. Once the files are in S3, moving an Account into a specific AWS Organization will trigger AWS Deployment to apply the bootstrap template for that specific Organizational Unit to that newly moved account.

Any changes in the future made to this repository such as its templates or parameters files will trigger an update to any bootstrap template applied on accounts throughout the Organization.

#### Bootstrapping Inheritance

When bootstrapping AWS Accounts you might have a large number of accounts that are all required to have the same baseline applied to them. For this reason we use a recursive search concept to apply base stacks *(and parameters)* to accounts. Lets take the following example.

```
bootstrap_repository
│   adfconfig.yml
│
└───adf-build
└───deployment
│    ------│   global.yml
│    ------│   regional.yml
│
│
│───banking
│   │
│   │ ───dev
│   ------│   regional.yml
│   ------│   global.yml
│   │ ───test
│   ------│   regional.yml
│   ------│   global.yml  
│   │ ───prod
│   ------│   regional.yml
│   ------│   global.yml
│

│
│───insurance  
│   │  
│   │ ───dev
│   ------│   regional.yml
│   ------│   global.yml
│   │ ───test
│   ------│   regional.yml
│   ------│   global.yml  
│   │ ───prod
│   ------│   regional.yml
│   ------│   global.yml
│
```

In the above example we have defined a different global and regional configuration for *each* of the OU's under our business unit's *(insurance and banking)*. This means, that any account we move into these OU's will apply the most specific template that they can. However, if we decided that `dev` and `test` would have the same base template we can change the structure to be as follows:

```
bootstrap_repository
│   adfconfig.yml
│   regional.yml  <== These will be used when specificity is lowest
│   global.yml
│
└───adf-build
└───deployment
│   -------- │   regional.yml
│   -------- │   global.yml
│
│───banking
│   │ ───prod
│   -------- │   regional.yml
│   -------- │   global.yml
│───insurance  
│   │ ───prod
│   -------- │   regional.yml
│   -------- │   global.yml
│
```

Now what we have done is removed two folder representations of the Organizational Units and moved our generic `test & dev` base stacks into the root of our repository *(as a single template)*. This means that any account move into an OU that cannot find its `regional.yml` or `global.yml` will recursively search one level up until it reaches the root. This same logic is applied for parameter files such as `regional-params.json` and `global-params.json`.

#### Regional Bootstrapping

When it comes to bootstrapping accounts with certain resources you may have a need for some of these resources to be regionally defined such as VPC's, Subnets, S3 Buckets etc. The optional `regional.yml` and associated `regional-params.json` files allow you to define what will be bootstrapped at a regional level. This means each region you specify in your *adfconfig.yml* will receive this base stack. The same is applied to updating the base stacks. When a new change comes in for any base template it will be updated for each of the regions specified in your adfconfig.yml. The Deployment account has a minimum required `regional.yml` file that you can find in *src/bootstrap_repository/deployment*. More can be added to this template as required however the existing resources not be removed.

#### Global Bootstrapping

Similar to [Regional Bootstrapping](#regional-bootstrapping) however defined at a global level. Resources such as IAM roles and other account wide resources should be placed in the `global.yaml` and optional associated parameters in `global-params.json` in order to have them applied to the account. Any global stack is deployed in same region you choose to deploy your [deployment account](#deployment-account) into. Global stacks are deployed and updated first whenever the bootstrapping or updating process occur to allow for any exports to be defined prior to regional stacks executing. The Deployment account has a minimum required `global.yml` file that you can find in *src/bootstrap_repository/deployment*. More can be added to this template as required however, the default resources should not be removed.

#### Bootstrapping Regions

When you setup the initial configuration for the AWS Deployment Framework you define your configuration in the [adfconfig.yml](#adfconfig.yml). This file defines the regions you will use for not only bootstrapping but which regions will later be used as targets for deployment pipelines. Be sure you read the section on *adfconfig* to understand how this ties in with bootstrapping.

For an example structure and minimal *template* and *parameters* see the folder structure of `src/bootstrap_repository`.

#### Bootstrapping Recommendations

We recommend to keep the bootstrapping templates for your accounts as thin as possible and to only include the absolute essentials for a given OUs baseline. The provided default `global.yml` contains the minimum resources for the frameworks functionality *(Roles)* which can be built upon if required.

### Pipelines

#### Pipeline Parameters

Each Pipeline you create may require some parameters that you pass in during its creation. The pipeline itself is created in AWS CloudFormation from one of the pipeline types in the [pipeline_types](#pipeline-types) folder *(src/pipelines_repository/pipeline_types)* on the deployment account. As a minimum, you will need to pass in a source account in which this pipeline will be linked to as an entry point.

The project name you specify in the deployment_map.yml will be automatically linked to a repository of the same name *(in the source account you chose)* so be sure to name your pipeline in the map correctly. The Notification endpoint is simply an endpoint that you will receive updates on when this pipeline has state changes *(via slack or email)*. The Source Account Id plays an important role by linking this specific pipeline to a specific account in which it can receive resources. For example, let's say we are in a team that deploys the CloudFormation template that contains the base networking and security to the Organization. In this case, this team may have their own AWS account which is completely isolated from the team that develops applications for the banking sector of the company.

The pipeline for this CloudFormation template should only ever be triggered by changes on the repository in that specific teams account. In this case, the Account Id for the team that is responsible for this specific CloudFormation will be entered in the parameters as **SourceAccountId** value.

When you enter an Account Id in the parameter file of a pipeline you are saying that this pipeline can only receive content *(trigger a run)* from a change on that specific repository in that specific account and on a specific branch *(defaults to master)*. This stops other accounts making repositories that might push code down an unintended pipeline since every pipeline maps to only one source.

Here is an example of passing in a parameter to a pipeline to override the default branch that is used to trigger the pipeline from.

```yaml
pipelines:
  - name: vpc
    type: github-cloudformation
    params:
      - Owner: github_owner
      - BranchName: dev/feature
    targets:
      - /security
```

**Note** If you find yourself specifying the same set of parameters over and over through-out the deployment map consider moving the value into the template itself *(in the pipelines_type folder)* as the default value.

#### Pipeline Types

In the [deployment map](#deployment-map) file you will notice that there is a property called **type**. This value maps directly the the type of pipeline you wish to use for that specific pipeline. As your organization grows you might have different needs for different types of pipelines. For example, one might handle all the CloudFormation deployment aspects however you might also want a pipeline that uses other third-party integrations for CodePipeline such as Jenkins or TeamCity, or maybe deploys directly to Lambda as opposed to using CloudFormation as a deployment configuration. In the deployment account pipelines repository, in the folder titled *pipeline_types* you can create the pipeline file that best suits your needs. From there you can add or update the deployment_map.yml file with the name of the pipeline file you wish to use. This allows you to create a pipeline once and have it used many times with a different combination of accounts and regions as targets.

Let's look at the `github-cloudformation.j2.yml` example that creates us a Webhook in our Github repository that triggers our Pipeline to run on any changes. The template itself is similar to the `cc-cloudformation.j2.yml` file with a few small differences. If we look at the parameters this template takes we can see the following:

```yaml
  WebhookSecret:
    Description: Webhook secret for Github
    Type: AWS::SSM::Parameter::Value<String>
    NoEcho: true
    Default: /tokens/webhook/github
  OAuthToken:
    Description: OAuthToken from Github
    Type: AWS::SSM::Parameter::Value<String>
    NoEcho: true
    Default: /tokens/oauth/github
```

In order for this template to generate a pipeline connected to Github you will need to create a Personal Access Token in Github that allows its connection to AWS CodePipeline. You can read more about creating a Token [here](https://docs.aws.amazon.com/codepipeline/latest/userguide/GitHub-rotate-personal-token-CLI.html). Once the token has been created you can store that in Parameter Store on the Deployment Account. The Webhook secret is a value you define and store in Parameter Store with a path of `/tokens/webhook/github` *(Can have different path if required)*. Ensure that you control access to [Parameter Store paths](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-access.html) with policies so that these values cannot be tampered with unintentionally.

Once the values are stored, you can create the Repository in Github as per normal. Once its created you do not need to do anything else on Github's side just update your [deployment map](#deployment-map) to use the new pipeline type and push to the deployment account. Here is an example of a deployment map with a single pipeline from Github, in this case the repository on github must be named 'vpc'.

```yaml
pipelines:
  - name: vpc
    type: github-cloudformation
    params:
      - Owner: github_owner
    targets:
      - /security
```

Pipeline files use the Jinja2 *(.j2)* preprocessor in order to dynamically generate the deployment phases of your pipeline. For more information on Jinja2 take a look at the [documentation](http://jinja.pocoo.org/docs/2.10/).

As a guide we provide a few examples for you to get going with `pipeline_types` such as `cc-cloudformation.yml.j2` and `github-cloudformation.yml.j2` however you can go on to create which type you desire.

## Service Control Policies
Service control policies (SCPs) are one type of policy that you can use to manage your organization. SCPs offer central control over the maximum available permissions for all accounts in your organization, allowing you to ensure your accounts stay within your organization’s access control guidelines. ADF allows SCPs to be applied in a similar fashion as base stacks. You can define your SCP definition in a file named `scp.json` and place it in a folder that represents your Organizational Unit within the `bootstrap_repository` folder.

SCPs aren't available if your organization has enabled only the consolidated billing features. SCPs are available only in an organization that has [all features enabled](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html). Once you have enabled all features within your Organization, ADF can manage and automate the application and updating process of the SCPs.

### Source Control

The AWS Deployment Framework allows you to use the supported AWS CodePipeline source types for source control which will act as entry points for your pipelines. Each of the options *(S3, AWS CodeCommit or Github)* have their own benefits when it comes to how they integrate with the ADF however they are interchangeable as desired. In order to use a different source type for your pipelines you will to define a pipeline type that uses the desired source control configuration. As a starting point you can find the *github-cloudformation.yml.j2* file in the *pipeline_types* folder that demonstrates how Github can be used as an entry point for your pipelines.

The same goes for any pipeline configuration for that matter, if you wish to use other Pipeline integrations just make a *pipeline_type* that defines your use case and tie a pipeline to it in the [deployment map](#deployment-map).

### Default Deployment Account Region

The Default Deployment account region is the region where the Pipelines you create and their associated [stacks](#pipeline-types) will reside. It is also the region that will host CodeCommit repositories *(If you choose to use CodeCommit)*. You can think of the Deployment Account region as the one that you would consider your default region of choice when deploying resources in AWS.

### Integrating Slack

The ADF allows alternate *NotificationEndpoint* values that can be used to notify the status of a specific pipeline *(in deployment_map.yml)*. You can specify an email address in the deployment map and notifications will be emailed directly to that address. However, if you specify a slack channel name *(eg my-team)* as the value, the notifications will be forwarded to that channel. In order to setup this integration you will need to create a [Slack App](https://api.slack.com/apps). When you create your Slack app, you can create multiple Webhook URL's *(Incoming Webhook)* that are each associated with their own channel. Create a webhook for each channel you plan on using throughout your Organization. Once created, copy the webhook URL and create a new parameter in Parameter Store on the Deployment Account with the type of 'SecureString'. Give the Parameter a name that maps to the channel that the webhook is authorized to send messages to. For example, if I had created a webhook for my team called `team-bugs` this would be stored in Parameter store as `/notification_endpoint/hooks/slack/team-bugs`. Ensure to encrypt the value with the CodePipeline KMS Key in that Deployment Account named: `alias/codepipeline-(account_id)`.

Once the value is encrypted in Parameter Store you can use the channel name as a reference in the deployment_map.yml file like:

```yaml
pipelines:
  - name: sample-vpc
    type: cc-cloudformation
    params:
      - SourceAccountId: 111112233332
      - NotificationEndpoint: team-bugs # This channel will receive pipeline events (success/failures/approvals)
      - RestartExecutionOnUpdate: True
    targets:
      - /banking/testing
      - /banking/production
```

Slack can also be used as the `main-notification-endpoint` in the `adfconfig.yml` file like so:

```yaml
  main-notification-endpoint:
    - type: slack
      target: deployments
```

As per the same as the `deployment_map.yml` style configuration, this would require that you have an incoming webhook configured for the *deployments* channel in your slack app, and that the value *(eg.. https://hooks.slack.com/services/XYZ....)* is stored as an encrypted string in Parameter Store *(using the same above KMS key)* on the deployment account *(in main deployment region)*.

### Updating Between Versions

To update ADF between *minor* releases you can run the same commands used to install ADF from the terminal with credentials in the master account. Pull from the changes from the master branch on Github and from the root of the repository run:

```bash
aws cloudformation package \
--template-file $PWD/src/initial/template.yml \
--s3-bucket MASTER_ACCOUNT_BUCKET_NAME \
--output-template-file $PWD/template-deploy.yml \
--region us-east-1

aws cloudformation deploy \
--stack-name aws-deployment-framework-base \
--template-file $PWD/template-deploy.yml \
--capabilities CAPABILITY_NAMED_IAM \
--parameter-overrides DeploymentAccountBucket=DEPLOYMENT_ACCOUNT_BUCKET_NAME \
OrganizationId=ORGANIZATION_ID \
--region us-east-1
```

Once complete, change directory in `src/bootstrap_repository` and make a new commit with the upstream changes included and push those into your `aws-deployment-framework-bootstrap` repository. Once complete do the same for changes in the `src/pipelines_repository` and its CodeCommit repository.