# Administrator Guide

- [Src Folder](#src-folder)
- [adfconfig](#adfconfig)
  - [Roles](#roles)
  - [Regions](#regions)
  - [Config](#config)
- [Accounts](#Accounts)
  - [Master](#master-account)
  - [Deployment](#deployment-account)
    - [Default Deployment Account Region](#default-deployment-account-region)
  - [Bootstrapping](#bootstrapping-accounts)
    - [Bootstrapping Overview](#bootstrapping-overview)
    - [Bootstrapping Inheritance](#bootstrapping-inheritance)
    - [Regional Bootstrapping](#regional-bootstrapping)
    - [Global Bootstrapping](#global-bootstrapping)
    - [Bootstrapping Regions](#bootstrapping-regions)
    - [Bootstrapping Recommendations](#bootstrapping-recommendations)
  - [Pipelines](#pipelines)
    - [Pipeline Parameters](#pipeline-parameters)
    - [Using Github](#using-github)
    - [Chaining Pipelines](#chaining-pipelines)
- [Service Control Policies](#service-control-policies)
- [Tagging Policies](#tagging-policies)
- [Pipelines](#pipelines)
  - [Pipeline Parameters](#pipeline-parameters)
  - [Chaining Pipelines](#chaining-pipelines)
- [Integrating Slack](#integrating-slack)
- [Updating Between Versions](#updating-between-versions)
- [Removing ADF](#removing-adf)

## Src Folder

The `src` folder contains a nesting of folders that go on to make two different git repositories. One of the repositories *(bootstrap)* lives on your AWS Master Account and is responsible for holding bootstrap AWS CloudFormation templates for your Organization that are used for setting up AWS Accounts with a foundation of resources to suit your needs. These templates are automatically applied to AWS accounts within specific AWS Organizations Organizational Units. The other repository *(pipelines)* lives on your *deployment* account and holds the various definitions that are used to facilitate deploying your applications and resources across many AWS Account and Regions. These two repositories will be automatically committed to AWS CodeCommit with the initial starting content as part of the initial deployment of ADF. From there, you can clone the repositories and extend the example definitions in them as desired.

## adfconfig

The `adfconfig.yml` file resides on the [Master Account](#master-account) CodeCommit Repository *(in us-east-1)* and defines the general high level configuration for the AWS Deployment Framework. These values from the value are synced into AWS Systems Manager Parameter Store and are used for certain orchestration options throughout your Organization. Below is an example of its contents. When you install ADF via the Serverless Application Repository, some of the information entered in the parameters will be passed into the *adfconfig.yml* that is committed to the bootstrap repository as a starting point, you can always edit it and push it back into the bootstrap repository to update any values.

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
- **scm** enables the automation aspect of creating AWS CodeCommit repositories automatically when creating a new Pipeline via ADF. This option is only relevant if you are using the *source_account_id* parameter in your Pipeline Parameters, if so, and this value is *enabled* ADF will automatically create the AWS CodeCommit Repository on the Source Account with the same name of the associated pipeline. If the Repository already exists on the source account this process will continue silently. If you wish to update/alter the CloudFormation template used to create this repository it can be found at */src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/repo_templates/codecommit.yml*.

## Accounts

### Master Account

The Master account *(also known as root)* is the owner of the AWS Organization. This account is the only account that is allowed to access AWS Organizations and make changes such as creating accounts or moving accounts the Organization. Because of this, it is important that you keep the account safe and [well structured](https://docs.aws.amazon.com/aws-technical-content/latest/cost-optimization-laying-the-foundation/aws-account-structure.html) when it comes to IAM access and controls. The AWS Deployment Framework does deploy minimal resources into the master account to allow processes such as [bootstrapping](#bootstrapping-accounts) and to take advantage of changes of structure within your AWS Organization. The CodeCommit repository on the Master accounts holds bootstrapping templates and parameters along with the `adfconfig.yml` file which defines how the framework orchestrates certain tasks. Any changes to resources such as `adfconfig.yml` or any bootstrapping template should be done via a Pull Request and the repository should apply strict IAM permissions surrounding merging of requests. This account is normally managed by some sort of centrally governed team who can translate business requirements or policies for Organizational Units into technical artifacts in the form of SCPs or CloudFormation templates that ADF will apply.

### Deployment Account

The Deployment Account is the gatekeeper for all deployments throughout an Organization. Once the baselines have been applied to your accounts via the bootstrapping process, the Deployment account connects the dots by taking source code and resources from a repository *(Github / CodeCommit / S3)* and into the numerous target accounts and regions as defined in the deployment map files via AWS CodePipeline. The Deployment account holds the [deployment_map.yml](#deployment_map) file(s) which defines where, what and how your resources will go from their source to their destination. In an Organization there should only be a single Deployment account. This is to promote transparency throughout an organization and to reduce duplication of code and resources. With a single Deployment Account teams can see the status of other teams deployments while still being restricted to making changes to the deployment map files via [Pull Requests](https://docs.aws.amazon.com/codecommit/latest/userguide/pull-requests.html).

#### Default Deployment Account Region

The Default Deployment account region is the region where the Pipelines you create and their associated [stacks](#pipeline_types) will reside. It is also the region that will host CodeCommit repositories *(If you choose to use CodeCommit)*. You can think of the Deployment Account region as the region that you would consider your default region of choice when deploying resources in AWS.

### Account Provisioning
ADF enables automated AWS Account creation and management via its Account Provisioning process. This process runs as part of the bootstrap pipeline and ensures the existence of AWS Accounts defined in *.yml* files within the *adf-accounts* directory. For more information on how how this works see the *readme.md* in the adf-accounts directory.

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
adf-bootstrap <-- This folder lives in the bootstrap repo on master account
│
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
adf-bootstrap <-- This folder lives in the bootstrap repo on master account
│   regional.yml  <== These will be used when specificity is lowest
│   global.yml
│
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

What we have done is removed two folder representations of the Organizational Units and moved our generic `test & dev` base stacks into the root of our repository *(as a single template)*. This means that any account move into an OU that cannot find its `regional.yml` or `global.yml` will recursively search one level up until it reaches the root. This same logic is applied for parameter files such as `regional-params.json` and `global-params.json` *(if they exist)*.

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

The name you specify in the *deployment_map.yml* *(or other map files)* will be automatically linked to a repository of the same name *(in the source account you chose)* so be sure to name your pipeline in the map correctly. The Notification endpoint is simply an endpoint that you will receive updates on when this pipeline has state changes *(via slack or email)*. The *source_account_id* plays an important role by linking this specific pipeline to a specific account in which it can receive resources. For example, let's say we are in a team that deploys the AWS CloudFormation template that contains the base networking and security to the Organization. In this case, this team may have their own AWS account which is completely isolated from the team that develops applications for the banking sector of the company.

The pipeline for this CloudFormation template should only ever be triggered by changes on the repository in that specific teams account. In this case, the AWS Account Id for the team that is responsible for this specific CloudFormation will be entered in the parameters as **source_account_id** value.

When you enter the *source_account_id* in the *deployment_map.yml**, you are saying that this pipeline can only receive content *(trigger a run)* from a change on that specific repository in that specific account and on a specific branch *(defaults to master)*. This stops other accounts making repositories that might push code down an unintended pipeline since every pipeline maps to only one source. Another common parameter used in pipelines is `restart_execution_on_update`, when this is set to *True* it will automatically trigger a run of the pipeline whenever its structure is updated. This is useful when you want a pipeline to automatically execute when a new account is moved into an Organizational Unit that a pipeline deploys into, such as foundational resources (eg VPC, IAM CloudFormation resources).


```yaml
pipelines:
  - name: vpc # <-- The CodeCommit repository on the source account would need to have this name
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 11111111111111 # <-- This teams AWS account is the only one able to push into this pipeline
    targets:
      - /security # Shorthand target example
```

Here is an example of passing in a parameter to a pipeline to override the default branch that is used to trigger the pipeline from, this time using Github as a source *(No need for source_account_id)*.


```yaml
pipelines:
  - name: vpc # The Github repo would have this name
    default_providers:
      source:
        provider: github
        properties:
          branch: dev/feature
          repository: example-vpc # Optional, above name property will be used if this is not specified
          owner: bundyfx
          oauth_token_path: /adf/github_token # The path in AWS Secrets Manager that holds the GitHub Oauth token, ADF only has access to /adf/ prefix in Secrets Manager
          json_field: token # The field (key) name of the json object stored in AWS Secrets Manager that holds the Oauth token
    targets:
      - /security # Shorthand example
```

**Note** If you find yourself specifying the same set of parameters over and over through-out the deployment map consider using [Yaml Anchors and Alias](./user-guide.md).

Along with Pipeline Parameters there can potentially be stage parameters if required. Take for example the following pipeline to perform ETL processing on workloads as they land in one Amazon S3 Bucket and, after transformed, moved into new Buckets in other AWS Accounts.

```yaml
  - name: sample-etl
    default_providers:
      source:
        provider: s3
        properties:
          source_account_id: 111111111111
          bucket_name: banking-etl-bucket-source
          object_key: input.zip
      deploy:
        provider: s3
    targets:
      - path: 222222222222
        regions: eu-west-1
        properties:
          bucket_name: account-blah-bucket-etl
          object_key: some_path/output.zip
      - path: 333333333333
        properties:
          bucket_name: business_unit_bucket-etl
          object_key: another/path/output.zip
```

In this example, we want to take our `input.zip` file from the Amazon S3 Bucket `banking-etl-bucket-source` that lives in the account `111111111111`. When the data lands in the bucket we want to run our pipeline which will run some ETL scripts *(see samples folder)* against the data and output `output.zip`. We then want to deploy this artifact into other Amazon S3 Buckets that live in other AWS Accounts and potentially other AWS Regions. Since Bucket Names are globally unique we need some way to define which bucket we want to deploy our `output.zip` into at a stage level. The way we accomplish this is we can pass in `properties` in the form of *key/value* into the stage itself.

#### Using Github

In order for a pipeline to be connected to Github you will need to create a Personal Access Token in Github that allows its connection to AWS CodePipeline. You can read more about creating a Token [here](https://docs.aws.amazon.com/codepipeline/latest/userguide/GitHub-rotate-personal-token-CLI.html). Once the token has been created you can store that in AWS Secrets Manager on the Deployment Account. The Webhook Secret is a value you define and store in AWS Secrets Manager with a path of `/adf/my_teams_token`. By Default, ADF only has read access access to Secrets with a path that starts with `/adf/`.

Once the values are stored, you can create the Repository in Github as per normal. Once its created you do not need to do anything else on Github's side just update your [deployment map](#./user-guide/#deployment-map) to use the new source type and push to the deployment account. Here is an example of a deployment map with a single pipeline from Github, in this case the repository on github must be named 'vpc'.

```yaml
pipelines:
  - name: vpc
    default_providers:
      source:
        provider: github
        properties:
          repository: example-vpc-adf # Optional, above name property will be used if this is not specified
          owner: bundyfx # Who owns this repository
          oauth_token_path: /adf/github_token # The path in AWS Secrets Manager that holds the GitHub Oauth token, ADF only has access to /adf/ prefix in Secrets Manager
          json_field: token # The field (key) name of the json object stored in AWS Secrets Manager that holds the Oauth token. example: if we stored {"token": "123secret"} - 'token' would be the json_field value.
    targets:
      - /security
```

#### Chaining Pipelines

Sometimes its a requirement to chain pipelines together, when one finishes you might want another one to start. Because of this, we have a *completion_trigger* property which can be added to any pipeline within your deployment map files. Chaining works by creating a CloudWatch event that triggers on completion of the pipeline to start one or many others. For example:

```yaml
pipelines:
  - name: sample-vpc
    default_providers:
      source: &generic_source
        provider: codecommit
        properties:
          account_id: 111111111111
    completion_trigger: # <--- When this pipeline finishes it will automatically start sample-iam and sample-ecs-cluster at the same time
        pipelines:
          - sample-iam
          - sample-ecs-cluster
    targets: &generic_targets # using YAML Anchor
      - /banking/testing
      - approval
      - /banking/production

  - name: sample-iam
    default_providers:
      source: *generic_source # using YAML Alias
    targets: *generic_targets # using YAML Alias

  - name: sample-ecs-cluster
    default_providers:
      source: *generic_source # using YAML Alias
    targets: *generic_targets # using YAML Alias
```

## Service Control Policies
Service control policies *(SCPs)* are one type of policy that you can use to manage your organization. SCPs offer central control over the maximum available permissions for all accounts in your organization, allowing you to ensure your accounts stay within your organization’s access control guidelines. ADF allows SCPs to be applied in a similar fashion as base stacks. You can define your SCP definition in a file named `scp.json` and place it in a folder that represents your Organizational Unit within the `adf-bootstrap` folder from the `aws-deployment-framework-bootstrap` repository on the Master Account.

SCPs are available only in an organization that has [all features enabled](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html). Once you have enabled all features within your Organization, ADF can manage and automate the application and updating process of the SCPs.

## Tagging Policies
Tag Policies are a feature that allows you to define rules on how tags can be used on AWS resources in your accounts in AWS Organizations. You can use Tag Policies to easily adopt a standardized approach for tagging AWS resources. You can define your Tagging Policy definition in a file named `tagging-policy.json` and place it in a folder that represents your Organizational Unit within the `adf-bootstrap` folder from the `aws-deployment-framework-bootstrap` repository on the Master Account.

Tag Policies are available only in an organization that has [all features enabled](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html). Once you have enabled all features within your Organization, ADF can manage and automate the application and updating process of the Tag Policies. For more information, see [here](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html).


## Integrating Slack

The ADF allows alternate *notification_endpoint* values that can be used to notify the status of a specific pipeline *(in deployment_map.yml)*. You can specify an email address in the deployment map and notifications will be emailed directly to that address. However, if you specify a slack channel name *(eg team-bugs)* as the value, the notifications will be forwarded to that channel. In order to setup this integration you will need to create a [Slack App](https://api.slack.com/apps). When you create your Slack app, you can create multiple Webhook URL's *(Incoming Webhook)* that are each associated with their own channel. Create a webhook for each channel you plan on using throughout your Organization. Once created, copy the webhook URL and create a new secret in Secrets Manager on the Deployment Account:

1. In AWS Console, click _Store a new secret_ and select type 'Other type of secrets' *(eg API Key)*.
2. In _Secret key/value_ tab, enter the channel name *(eg team-bugs)* in the first field and the webhook URL in the second field.
3. In _Select the encryption key_ section, choose *aws/secretsmanager* as the encryption key. Click _Next_.
4. In _Secret Name_, give the secret a name that maps to the channel that the webhook is authorized to send messages to. For example, if I had created a webhook for a channel called `team-bugs` this would be stored in Secrets Manager as `/adf/slack/team-bugs`.
5. Optionally, enter a description for the key
6. Click _Next_. Ensure *Disable automatic rotation* is selected. Click _Next_ again.
7. Review the data and then click _Store_.

Once the value is stored as a secret, it can be used like so:

```yaml
pipelines:
  - name: sample-vpc
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111112233332
    params:
      notification_endpoint: team-bugs # This channel will receive pipeline events (success/failures/approvals)
      restart_execution_on_update: True
    targets:
      - path: /banking/testing
        name: testing
      - path: /banking/production
        name: omg_production
```

## Updating Between Versions

To update ADF between releases, open the Serverless Application Repository *(SAR)* on the master account in **us-east-1**. From here, search for *adf* and click deploy. During an update of ADF there is no need to pass in any parameters other than the defaults *(granted you used the defaults to deploy initially)*.

This will cause your *serverlessrepo-aws-deployment-framework* stack to update with any new changes that were included in that release of ADF. However, there might be changes to some of the foundational aspects of ADF and how it works *(eg CDK Constructs)*, because of this, there might be changes to the files that live within the *bootstrap* repository in your AWS account. To do this, AWS CloudFormation will run the *InitialCommit* Custom CloudFormation resource when updating via the SAR, this resource will open a pull request against the current *master* branch on the *bootstrap* repository with a set of changes that you can optionally choose to merge. If those changes are merged into master, the bootstrap pipeline will run to finalize the update to the latest version.

## Removing ADF

If you wish to remove ADF you can delete the CloudFormation stack named *serverlessrepo-aws-deployment-framework* within on the master account in the us-east-1 region. This will move into a DELETE_FAILED at some stage because there is an S3 Bucket that is created via a custom resource *(cross region)*. After it moves into DELETE_FAILED, you can right-click on the stack and hit delete again while selecting to skip the Bucket the stack will successfully delete, you can then manually delete the bucket and its contents. After the main stack has been removed you can remove the base stack in the deployment account *adf-global-base-deployment* and any associated regional deployment account base stacks. After you have deleted these stacks, you can manually remove any base stacks from accounts that were bootstrapped. Alternatively prior to removing the initial *serverlessrepo-aws-deployment-framework* stack, you can set the *moves* section of the *adfconfig.yml* file to *remove-base* which would automatically clean up the base stack when the account is moved to the Root of the AWS Organization.

One thing to keep in mind if you are planning to re-install ADF is that you will want to clean up the parameter from SSM Parameter Store named *deployment_account_id* within us-east-1 on the master account. AWS Step Functions uses this parameter to determine if ADF has already got a deployment account setup, if you re-install ADF with this parameter set with a value, ADF will attempt an assume role to the account to do some work, which will fail since that role will not be on the account at that point.

There is also a CloudFormation stack named *adf-global-base-adf-build* which lives on the master account in your main deployment region. This stack creates two roles on the master account after the deployment account has been setup. These roles allow the deployment accounts CodeBuild role to assume a role back to the master account in order to query Organizations for AWS Accounts. This stack must be deleted manually also, if you do not remove this stack and then perform a fresh install of ADF, AWS CodeBuild on the deployment account will not be able to assume a role to the master account to query AWS Organizations. This is because this specific stack creates IAM roles with a strict trust relationship to the CodeBuild role on the deployment account, if that role gets deleted *(Which is will when you delete adf-global-base-deployment)* then this stack references invalid IAM roles that no longer exist. If you forget to remove this stack and notice the trust relationship of the IAM roles referenced in the stack are no longer valid, you can delete the stack and re-run the main bootstrap pipeline which will recreate it with valid roles and links to the correct roles.
