# Administrator Guide

- [Src Folder](#src-folder)
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
  - [Chaining Pipelines](#chaining-pipelines)
- [Default Deployment Account Region](#default-deployment-account-region)
- [Integrating Slack](#integrating-slack)
- [Updating Between Versions](#updating-between-versions)
- [Removing ADF](#removing-adf)


## Src Folder

The `src` folder contains a nesting of folders that go on to make two different git repositories. One of the repositories *(bootstrap)* lives on your AWS Master Account and is responsible for holding bootstrap AWS CloudFormation templates for your Organization that are used for bootstrapping AWS Accounts, these templates are automatically applied to accounts within specific AWS Organizations Organizational Units. The other repository *(pipelines)* lives on your *deployment* account and holds the various definitions and configuration that are used to facilitate deploying your applications and resources across many AWS Account and Regions. These two repositories will be automatically committed to AWS CodeCommit with the initial starting content as part of the initial deployment of ADF. From there, you can clone the repositories and work on alter the configuration in them as desired.


## adfconfig

The `adfconfig.yml` file resides on the [Master Account](#master-account) and defines the general high level configuration for the AWS Deployment Framework. These values from the value are synced into AWS Systems Manager Parameter Store and are used for certain orchestration options throughout your Organization. Below is an example of its contents. When you install ADF via the Serverless Application Repository, some of the information entered in the parameters will be passed into the *adfconfig.yml* that is committed to the bootstrap repository as a starting point, you can always edit it and push it back into the bootstrap repository to update any values.

```yaml
roles:
  cross-account-access: OrganizationAccountAccessRole

regions:
  deployment-account:
    - eu-central-1
  targets: # No need to also include 'eu-central-1' in targets as the deployment-account region is also considered a target region by default.
    - eu-west-1

config:
  main-notification-endpoint:
    - type: email
      target: john@doe.com
  moves:
    - name: to-root
      action: safe
  protected: # Optional
    - ou-123
  scp: # Service Control Policy
    keep-default-scp: enabled # Optional
  scm: # Source Control Management
    auto-create-repositories: enabled # Optional
```

In the above example we have four main properties in `roles`, `regions` and `config`.

#### Roles

Currently, the only role type specification that the *adfconfig.yml* file requires is the role **name** you wish to use for cross account access. The AWS Deployment Framework requires an role that will be used to initiate bootstrapping and allow the [Master Account](#master-account) access to assume access in target accounts to facilitate bootstrapping and updating processes. When you create new accounts in your AWS Organization they will all need to be instantiated with a role of this same name. When creating a new account, by default, the role you choose as the [Organization Access role](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html) comes with Administrator Privileges in IAM.

#### Regions
The Regions specification plays an important role in how ADF is laid out. You should choose a single `deployment-account` region that you would consider your primary region of choice. You should also define target regions you would like to apply baselines to *and* have as deployment targets for your pipelines. If you decide to add more regions later that is also fine. If you add a new region to this list and push the *aws-deployment-framework-bootstrap* repository to the master account it will apply the bootstrapping process to all of your existing accounts for the new region added. You can **not** have AWS CodePipeline deployment pipelines deploy into regions that are not part of this list of bootstrapped regions. In the above example we want our main region to be the `eu-central-1` region, this region, along with `eu-west-1` will now be able to have resources bootstrapped and deployed into via AWS CodePipeline.

#### Config

Config has five components in `main-notification-endpoint`, `scp`, `scm`, `moves` and `protected`.

- **main-notification-endpoint** is the main notification endpoint for the bootstrapping pipeline and deployment account pipeline creation pipeline. This value should be a valid email address or [slack](./admin-guide/#integrating-slack) channel that will receive updates about the status *(Success/Failure)* of CodePipeline that is associated with bootstrapping and creation/updating of all pipelines throughout your organization.
- **moves** is configuration related to moving accounts within your AWS Organization. Currently the only configuration options for `moves` is named *to-root* and allows either `safe` or `remove_base`. If you specify *safe* you are telling the framework that when an AWS Account is moved from whichever OU it currently is in, back into the root of the Organization it will not make any direct changes to the account. It will however update any AWS CodePipeline pipelines that the account belonged to so that it is no longer a valid target. If you specify `remove_base` for this option and move an account to the root of your organization it will attempt to remove the base CloudFormation stacks *(regional and global)* from the account and then update any associated pipeline.
- **protected** is a configuration that allows you to specify a list of OUs that are not configured by the AWS Deployment Framework bootstrapping process. You can move accounts to the protected OUs which will skip the standard bootstrapping process. This is useful for migrating existing accounts into being managed by The ADF.
- **scp** allows the definition of configuration options that relate to Service Control Policies. Currently the only option for *scp* is *keep-default-scp* which can either be *enabled* or *disabled*. This option determines if the default FullAWSAccess Service Control Policy should stay attached to OUs that are managed by an *scp.json* or if it should be removed to make way for a more specific SCP, by default this is *enabled*. Its important to understand how SCPs work before setting this setting to disabled. Please read [How SCPs work](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_about-scps.html) for more information.
- **scm** enables the automation aspect of creating AWS CodeCommit repositories automatically when creating a new Pipeline via ADF. This option is only relevant if you are using the *SourceAccountId* parameter in your Pipeline Parameters, if so, and this value is *enabled* ADF will automatically create the AWS CodeCommit Repository on the Source Account with the same name of the associated pipeline. If the Repository already exists on the source account this process will continue silently. If you wish to update/alter the CloudFormation template used to create this repository it can be found at */src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/repo_templates/codecommit.yml*.

## Accounts

### Master Account

The Master account *(also known as root)* is the owner of the AWS Organization. This account is the only account that is allowed to access AWS Organizations and make changes such as creating accounts or moving accounts the Organization. Because of this, it is important that you keep the account safe and [well structured](https://docs.aws.amazon.com/aws-technical-content/latest/cost-optimization-laying-the-foundation/aws-account-structure.html) when it comes to IAM access and controls. The AWS Deployment Framework does deploy minimal resources into the master account to allow processes such as [bootstrapping](#bootstrapping-accounts) and to take advantage of changes of structure within your AWS Organization. The CodeCommit repository on the Master accounts holds bootstrapping templates and parameters along with the `adfconfig.yml` file which defines how the framework orchestrates certain tasks. Any changes to resources such as `adfconfig.yml` or any bootstrapping template should be done via a Pull Request and the repository should apply strict IAM permissions surrounding merging of requests. This account is normally managed by some sort of centrally governed team who can translate business requirements or policies for Organizational Units into technical artifacts in the form of SCPs or CloudFormation templates that ADF will apply.

### Deployment Account

The Deployment Account is the gatekeeper for all deployments throughout an Organization. Once the baselines have been applied to your accounts via the bootstrapping process, the Deployment account connects the dots by taking source code and resources from a repository *(Github / CodeCommit / S3)* and into the numerous target accounts and regions as defined in the deployment map. The Deployment account holds the [deployment_map.yml](#deployment_map) file which defines where, what and how your resources will go from their source to their destination. In an Organization there should only be a single Deployment account. This is to promote transparency throughout an organization and to reduce duplication of code and resources. With a single Deployment Account teams can see the status of other teams deployments while still being restricted to making changes to the `deployment_map.yml` via [Pull Requests](https://docs.aws.amazon.com/codecommit/latest/userguide/pull-requests.html).

### Bootstrapping Accounts

#### Bootstrapping Overview

The Bootstrapping of AWS an Account is a concept that allows you to specify an AWS CloudFormation template that will automatically be applied any account that is moved into a specific Organizational Unit in AWS Organizations. Bootstrapping of AWS accounts is a convenient way to apply a baseline to an account or sub-set of accounts based on the structure of your AWS Organization.

When deploying ADF via the Serverless Application Repository, a CodeCommit repository titled `aws-deployment-framework-bootstrap` will also be created. This repository acts as an entry point for bootstrapping templates. The definition of which templates are applied to which Organization Unit are defined in the folder structure of the `aws-deployment-framework-bootstrap` repository.

Create a folder structure and associated CloudFormation templates *(global.yml)* or *(regional.yml)* and optional parameters *(global-params.json)* or *(regional-params.json)* that match your desired specificity when bootstrapping your AWS Accounts. Commit and push this repository to the CodeCommit repository titled `aws-deployment-framework-bootstrap` on the master account. The `regional.yml` is optional however the base configuration required for the ADF to funtion as intended in the default `global.yml` in the base of the *bootstrap repository* repository.

Pushing to this repository will initiate AWS CodePipeline to run which will in-turn start AWS CodeBuild to sync the contents of the repository with S3. Once the files are in S3, moving an Account into a specific AWS Organization will trigger AWS Step Functions to run and to apply the bootstrap template for that specific Organizational Unit to that newly moved account.

Any changes in the future made to this repository such as its templates contents or parameters files will trigger an update to any bootstrap template applied on accounts throughout the Organization. You can see these changes in CodePipeline. The  SAR Applications creates a bootstrap pipeline named `aws-deployment-framework-bootstrap-pipeline`.

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

What we have done is removed two folder representations of the Organizational Units and moved our generic `test & dev` base stacks into the root of our repository *(as a single template)*. This means that any account move into an OU that cannot find its `regional.yml` or `global.yml` will recursively search one level up until it reaches the root. This same logic is applied for parameter files such as `regional-params.json` and `global-params.json`.

#### Regional Bootstrapping

When it comes to bootstrapping accounts with certain resources you may have a need for some of these resources to be regionally defined such as VPC's, Subnets, S3 Buckets etc. The optional `regional.yml` and associated `regional-params.json` files allow you to define what will be bootstrapped at a regional level. This means each region you specify in your *adfconfig.yml* will receive this base stack. The same is applied to updating the base stacks. When a new change comes in for any base template it will be updated for each of the regions specified in your adfconfig.yml. The Deployment account has a minimum required `regional.yml` file that is part of the initial commit of the skeleton content. More can be added to this template as required however the existing resources should not be removed.

#### Global Bootstrapping

Similar to [Regional Bootstrapping](#regional-bootstrapping) however defined at a global level. Resources such as IAM roles and other account wide resources should be placed in the `global.yaml` and optional associated parameters in `global-params.json` in order to have them applied to accounts. Any global stack is deployed in same region you choose to deploy your [deployment account](#deployment-account) into. Global stacks are deployed and updated first whenever the bootstrapping or updating process occur to allow for any exports to be defined prior to regional stacks executing. The Deployment account has a minimum required `global.yml` file that is included as part of the initial commit. More can be added to this template as required however, the default resources should not be removed.

#### Bootstrapping Regions

When you setup the initial configuration for the AWS Deployment Framework you define your parameters in the Serverless Application Repository, some of these details get placed into the [adfconfig.yml](#adfconfig.yml). This file defines the regions you will use for not only bootstrapping but which regions will later be used as targets for deployment pipelines. Be sure you read the section on *adfconfig* to understand how this ties in with bootstrapping.

#### Bootstrapping Recommendations

We recommend to keep the bootstrapping templates for your accounts as light as possible and to only include the absolute essentials for a given OUs baseline. The provided default `global.yml` contains the minimum resources for the frameworks functionality *(Roles)* which can be built upon if required.

### Pipelines

#### Pipeline Parameters

Each Pipeline you create may require some parameters that you pass in during its creation. The pipeline itself is created in AWS CloudFormation from one of the pipeline types in the [pipeline_types](#pipeline-types) folder in your *aws-deployment-framework-pipelines* repository on the Deployment account. As a minimum *(if you are using CodeCommit)*, you will need to pass in a source account in which this pipeline will be linked to as an entry point.

The name you specify in the *deployment_map.yml* will be automatically linked to a repository of the same name *(in the source account you chose)* so be sure to name your pipeline in the map correctly. The Notification endpoint is simply an endpoint that you will receive updates on when this pipeline has state changes *(via slack or email)*. The *SourceAccountId* plays an important role by linking this specific pipeline to a specific account in which it can receive resources. For example, let's say we are in a team that deploys the AWS CloudFormation template that contains the base networking and security to the Organization. In this case, this team may have their own AWS account which is completely isolated from the team that develops applications for the banking sector of the company.

The pipeline for this CloudFormation template should only ever be triggered by changes on the repository in that specific teams account. In this case, the AWS Account Id for the team that is responsible for this specific CloudFormation will be entered in the parameters as **SourceAccountId** value.

When you enter the *SourceAccountId* in the *deployment_map.yml**, you are saying that this pipeline can only receive content *(trigger a run)* from a change on that specific repository in that specific account and on a specific branch *(defaults to master)*. This stops other accounts making repositories that might push code down an unintended pipeline since every pipeline maps to only one source. Another common parameter used in pipelines is `RestartExecutionOnUpdate`, when this is set to *True* it will automatically trigger a run of the pipeline whenever its structure is updated. This is useful when you want a pipeline to automatically execute when a new account is moved into an Organizational Unit that a pipeline deploys into, such as foundational resources (eg VPC, IAM CloudFormation resources).


```yaml
pipelines:
  - name: vpc # <-- The CodeCommit repository on the source account would need to have this name
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111 # <-- This teams account is the only one able to push into this pipeline
    targets:
      - /security # Shorthand target example
```

Here is an example of passing in a parameter to a pipeline to override the default branch that is used to trigger the pipeline from, this time using Github as a source *(No need for SourceAccountId)*.


```yaml
pipelines:
  - name: vpc # The Github repo would have this name
    type: github-cloudformation
    params:
      - Owner: bundyfx # <-- The owner of the Repository on Github
      - BranchName: dev/feature
    targets:
      - /security # Shorthand example
```

**Note** If you find yourself specifying the same set of parameters over and over through-out the deployment map consider moving the value into the template itself *(in the pipelines_type folder)* as the default value.

Along with Pipeline Parameters there can potentially be stage parameters if required. Take for example the following pipeline to perform ETL processing on workloads as they land in one Amazon S3 Bucket and, after transformed, moved into new Buckets in other AWS Accounts.

```yaml
  - name: sample-etl
    type: s3-s3
    params:
      - SourceAccountId: 111111111111
      - SourceAccountBucket: banking-etl-bucket-source
      - SourceObjectKey: input.zip
    targets:
      - path: 222222222222
        regions: eu-west-1
        params:
          OutputBucketName: account-blah-bucket-etl
          OutputObjectKey: some_path/output.zip
      - path: 333333333333
        params:
          OutputBucketName: business_unit_bucket-etl
          OutputObjectKey: another/path/output.zip
```

In this example, we want to take our `input.zip` file from the Amazon S3 Bucket `banking-etl-bucket-source` that lives in the account `111111111111`. When the data lands in the bucket we want to run our pipeline which will run some ETL scripts *(see samples folder)* against the data and output `output.zip`. We then want to deploy this artifact into other Amazon S3 Buckets that live in other AWS Accounts and potentially other AWS Regions. Since Bucket Names are globally unique we need some way to define which bucket we want to deploy our `output.zip` into at a stage level. The way we accomplish this is we can pass in `params` in the form of *key/value* into the stage itself. This key/value pairs go directly into the pipeline type definition and can be referenced as required.


#### Pipeline Types

In the [deployment map](#./user-guide/#deployment-map) file you will notice that there is a property called **type**. This value maps directly the the type of pipeline you wish to use for that specific pipeline. As your organization grows you might have different needs for different types of pipelines. For example, one might handle all the CloudFormation deployment aspects however you might also want a pipeline that uses other third-party integrations for CodePipeline such as Jenkins or TeamCity, or maybe deploys directly to Lambda as opposed to using CloudFormation as a deployment configuration. In the deployment account pipelines repository, in the folder titled *pipeline_types* you can create the pipeline file that best suits your needs. From there you can add or update the deployment_map.yml file with the name of the pipeline file you wish to use. This allows you to create a pipeline once and have it used many times with a different combination of accounts and regions as targets.

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

Once the values are stored, you can create the Repository in Github as per normal. Once its created you do not need to do anything else on Github's side just update your [deployment map](#./user-guide/#deployment-map) to use the new pipeline type and push to the deployment account. Here is an example of a deployment map with a single pipeline from Github, in this case the repository on github must be named 'vpc'.

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

As a guide we provide a few examples for you to get going with `pipeline_types` such as `cc-cloudformation.yml.j2` and `github-cloudformation.yml.j2` however you can go on to create whichever type you desire.

#### Chaining Pipelines

Sometimes its a need to chain pipelines together, when one finishes you might want another one to start, or maybe another five? Because of this, we have a *completion_trigger* property which can be added to any pipeline within your deployment map files. Chaining works by creating a CloudWatch event that triggers on completion of the pipeline to start one or many others. For example:

```yaml
pipelines:
  - name: sample-vpc
    type: cc-cloudformation
    deployment_role: some_specific_role # <-- you can pass an optional IAM role of your choice that will be used as the deployment role for this pipeline
    completion_trigger: # <--- When this pipeline finishes it will automatically start sample-iam and sample-ecs-cluster at the same time
        pipelines:
          - sample-iam
          - sample-ecs-cluster
    params:
      - SourceAccountId: 1111111111111
    targets:  # Deployment stages
      - /banking/testing
      - approval
      - /banking/production

  - name: sample-iam
    type: cc-cloudformation
    params:
      - SourceAccountId: 1111111111111
    targets:
      - /banking/testing
      - approval
      - /banking/production

  - name: sample-ecs-cluster
    type: cc-cloudformation
    params:
      - SourceAccountId: 9999999999999
    targets:
      - /banking/testing
      - approval
      - /banking/production
```

## Service Control Policies
Service control policies *(SCPs)* are one type of policy that you can use to manage your organization. SCPs offer central control over the maximum available permissions for all accounts in your organization, allowing you to ensure your accounts stay within your organization’s access control guidelines. ADF allows SCPs to be applied in a similar fashion as base stacks. You can define your SCP definition in a file named `scp.json` and place it in a folder that represents your Organizational Unit within the `bootstrap_repository` folder.

SCPs are available only in an organization that has [all features enabled](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html). Once you have enabled all features within your Organization, ADF can manage and automate the application and updating process of the SCPs.

### Source Control

The AWS Deployment Framework allows you to use the supported AWS CodePipeline source types for source control which will act as entry points for your pipelines. Each of the options *(S3, AWS CodeCommit or Github)* have their own benefits when it comes to how they integrate with the ADF however they are interchangeable as desired. In order to use a different source type for your pipelines you will to define a pipeline type that uses the desired source control configuration. As a starting point you can find the *github-cloudformation.yml.j2* file in the *pipeline_types* folder that demonstrates how Github can be used as an entry point for your pipelines.

The same goes for any pipeline configuration for that matter, if you wish to use other Pipeline integrations just make a *pipeline_type* that defines your use case and tie a pipeline to it in the [deployment map](#./user-guide/#deployment-map).

### Default Deployment Account Region

The Default Deployment account region is the region where the Pipelines you create and their associated [stacks](#pipeline_types) will reside. It is also the region that will host CodeCommit repositories *(If you choose to use CodeCommit)*. You can think of the Deployment Account region as the region that you would consider your default region of choice when deploying resources in AWS.

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
      - path: /banking/testing
        name: testing
      - path: /banking/production
        name: omg_production
```

Slack can also be used as the `main-notification-endpoint` in the `adfconfig.yml` file like so:

```yaml
  main-notification-endpoint:
    - type: slack
      target: deployments
```

As per the same as the `deployment_map.yml` style configuration, this would require that you have an incoming webhook configured for the *deployments* channel in your slack app, and that the value *(eg.. https://hooks.slack.com/services/XYZ....)* is stored as an encrypted string in Parameter Store *(using the same above KMS key)* on the deployment account *(in main deployment region)*.

### Updating Between Versions

To update ADF between releases, open the Serverless Application Repository *(SAR)* on the master account in us-east-1. From here, search for *adf* and click deploy. During an update of ADF there is no need to pass in any parameters other than the defaults *(granted you used the defaults to deploy initially)*.

This will cause your *serverlessrepo-aws-deployment-framework* stack to update with any new changes that were included in that release of ADF. However, we also might make changes to some of the foundational aspects of ADF and how it works, because of this, we might want to change files that live within the *bootstrap* or *pipelines* repository with AWS CodeCommit on your account. To do this, AWS CloudFormation will run the *InitialCommit* Custom CloudFormation resource when updating via the SAR, this resource will open a pull request against the current *master* branch on the respective repositories with a set of changes that you can optionally choose to merge. Initially when updating via the SAR a PR will be opened if there are any changes to make against the *bootstrap* repository, if those are merged the bootstrap pipeline will run and will update the deployment account base stack, which will in-turn make a PR against the deployment accounts *pipeline* repository with any changes from upstream.


### Removing ADF

If you wish to remove ADF you can delete the CloudFormation stack named *serverlessrepo-aws-deployment-framework* within on the master account in us-east-1. This will move into a DELETE_FAILED at some stage because there is an S3 Bucket that is created via a custom resource *(cross region)*. After it moves into DELETE_FAILED, you can right-click on the stack and hit delete again while selecting to skip the Bucket the stack will successfully delete, you can then manually delete the bucket and its contents. After the main stack has been removed you can remove the base stack in the deployment account *adf-global-base-deployment* and any associated regional deployment account base stacks. After you have deleted these stacks, you can manually remove any base stacks from accounts that were bootstrapped. Alternatively prior to removing the initial *serverlessrepo-aws-deployment-framework* stack, you can set the *moves* section of the *adfconfig.yml* file to *remove-base* which would automatically clean up the base stack when the account is moved to the Root of the AWS Organization.

One thing to keep in mind if you are planning to re-install ADF is that you will want to clean up the parameter *deployment_account_id* within us-east-1 on the master account. AWS Step Functions uses this parameter to determine if ADF has already got a deployment account setup, if you re-install ADF with this parameter set with a value, ADF will attempt an assume role to the account to do some work, which will fail since that role will not be on the account at that point.

There is also a CloudFormation stack named *adf-global-base-adf-build* which lives on the master account in your main deployment region. This stack creates two roles on the master account after the deployment account has been setup. These roles allow the deployment accounts CodeBuild role to assume a role back to the master account in order to query Organizations for AWS Accounts. This stack must be deleted manually also, if you do not remove this stack and then perform a fresh install of ADF, AWS CodeBuild on the deployment account will not be able to assume a role to the master account to query AWS Organizations. This is because this specific stack creates IAM roles with a strict trust relationship to the CodeBuild role on the deployment account, if that role gets deleted *(Which is will when you delete adf-global-base-deployment)* then this stack references invalid IAM roles that no longer exist. If you forget to remove this stack and notice the trust relationship of the IAM roles referenced in the stack are no longer valid, you can delete the stack and re-run the main bootstrap pipeline which will recreate it with valid roles and links to the correct roles.
