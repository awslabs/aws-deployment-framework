# Installation Guide

## Prerequisites

- [awscli](https://aws.amazon.com/cli/).
- [git](https://git-scm.com/)
  - [AWS CodeCommit Setup](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html)
- [docker](https://docs.docker.com/get-docker/)

The steps in this guide should be performed in the AWS Organizations Management
account.

## Compatibility with AWS Control Tower

ADF is fully compatible with [AWS Control Tower](https://aws.amazon.com/de/controltower/).
ADF augments AWS Control Tower. A common operations model is defined as follows:

- AWS Control Tower is responsible for AWS Account creation and Organization
  Unit (OU) mapping.
- ADF is responsible for deploying applications as defined in the ADF
  deployment maps.

In the following, we assume that you install ADF without AWS Control Tower.
However, if a specific installation step requires a "AWS Control Tower-specific
action, we call those out explicitly.

It is okay to install ADF and AWS Control Tower in different regions.
For example:

- Install AWS Control Tower in `eu-central-1`.
- Install ADF in `us-east-1` or `cn-north-1`.

**If you want to use ADF and AWS Control Tower, we recommend that you setup
AWS Control Tower prior to installing ADF.**

---------------------------------

## 1. Enable Services

### 1.1. Enable CloudTrail

Ensure you have setup [AWS CloudTrail](https://aws.amazon.com/cloudtrail/)
*(Not the default trail)* in your Management Account that spans **all
regions**, the trail itself can be created in any region. Events [triggered via
CloudTrail](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_incident-response.html)
for AWS Organizations can only be acted upon in the us-east-1 (North Virginia) or `cn-northwest-1`
region.

Please use the [AWS CloudTrail
instructions](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html)
to configure the CloudTrail in the `us-east-1` or `cn-north-1` region within the AWS
Organizations Management AWS Account.

### 1.2. Enable AWS Organizations API Access

ADF will setup and configure [AWS
Organizations](https://us-east-1.console.aws.amazon.com/organizations/v2/home?region=us-east-1)
automatically.

However, ADF requires, but does not configure AWS Account Management
automatically.

Without configuring AWS Account Management, the `adf-account-management` Step
Functions state machine will fail to configure the AWS accounts such as the
deployment account for you. The error message that it would return would state:

> An error occurred (AccessDeniedException) when calling the ListRegions operation:
> User: arn:[...assumed-sts-role-arn...]/adf-account-management-config-region
> is not authorized to perform: account:ListRegions
> (Your organization must first enable trusted access with AWS Account Management.)

To enable this, go to AWS Organizations service console after it is configured
and [enable AWS Account Management via this
link](https://us-east-1.console.aws.amazon.com/organizations/v2/home/services/AWS%20Account%20Management).

## 2. Setup Your Build Environment

### 2.1. Local Instructions

For the following steps, we need to work on a Linux/Unix/macOS environment.
Additionally, you need to have AWS credentials configured to perform the
deployment actions in the AWS Organization Management account.

Please note that building on *Windows* is not supported, please use the
[Cloud9 instructions](#22-cloud9-instructions) below instead.

- [git](https://git-scm.com/)
  - To test if it is available, run `git --version`.
    This should return version 2.30 or later.
- [docker](https://docs.docker.com/get-docker/)
  - To test if it is available, run: `docker ps -a`.
    This should return a table that is possibly empty.
  - Additionally, running `docker --version` should return version 19 or
    later.
- [make](https://www.gnu.org/software/make/)
  - To test if it is available, run `make --version`.
    This should return 4.3 or later.
- [python 3](https://www.python.org/downloads/)
  - To test if it is available, run `python --version`.
    This should return 3.9 or later.
- [jq](https://github.com/jqlang/jq)
  - To test if it is available, run `jq --version`.
    This version should be 1.6 or later.
- [sed](https://www.gnu.org/software/sed/)
  - To test if it is available, run `sed --version`.
    This should return 4.3 or later.
  - If you have BSD sed installed, as is by default on macOS.
    You can test if it works with:
    `echo 'does sed work' | sed 's/does.*work/sed works/g'`

Install or update the above requirements as needed.
Alternatively, jump to the [Cloud9 instructions](#22-cloud9-instructions) instead
to use a cloud development machine to get started quickly.

After your environment is setup, please follow the [Build and Deploy
instructions)](#3-build-and-deploy-instructions) to continue.

### 2.2. Cloud9 Instructions

These instructions help setup and configure your Cloud9 instance to build
and deploy ADF with in case your local environment did not meet the
requirements. If your local setup is configured and working, feel free to skip
this section and jump to the [Build and Deploy
instructions)](#3-build-and-deploy-instructions) instead.

Read this [guide](https://docs.aws.amazon.com/cloud9/latest/user-guide/welcome.html)
to learn about AWS Cloud9 and how-to get started.

Either deploy the Cloud9 in the management account itself, or configure AWS
credentials such that you can perform actions in the AWS Management account.

Please pick an AWS Cloud9 compatible region to run the instance from.
During the deployment action of ADF, it will ask to perform the deployment
in the AWS Organizations control-plane region. Obviously, the credentials
available or configured in the Cloud9 instance should have access rights to
deploy ADF in the management account in that region.

The Cloud9 instance is needed to build and deploy ADF. Feel free to delete
the Cloud9 environment after ADF is deployed successfully.

#### 2.2.1. EC2 Instance

Any instance type would work.

The platform should be: **Amazon Linux 2023** or **Ubuntu Server 22.04 LTS**
or later.

#### 2.2.2. Network Settings

To build and deploy ADF, you will need to setup a Cloud9 environment that has
credentials setup. The recommended approach as documented
[here](https://docs.aws.amazon.com/cloud9/latest/user-guide/credentials.html)
is to use AWS Managed Temporary Credentials. In Cloud9, it will be able
to operate with your access rights (similarly to how AWS CloudShell works) if
you set it up:

- With SSM, no-ingress. Please note, use SSM as in AWS Systems Manager, *not*
  SSH.
- Leave VPC to the default, or place the machine in a public subnet.

#### 2.2.3. Free Disk Space

Once the instance is created, you need at least 16 GB of free disk space.
Unfortunately, the default Cloud9 instance volume is too small.

To change this, the quickest solution is to open the Cloud9 IDE and follow
the [resize the EBS volume guide in the Cloud9
documentation](https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html#move-environment-resize).

At the moment of writing, the volume Cloud9 creates is 10 GB, with around 2 GB
of free space. It is recommended to increase this to: **24 GB or larger**.

Please confirm the free disk space is large enough by running:

```bash
df -h $PWD
```

## 3. Build and Deploy Instructions

### 3.1. Clone The Repository

If this is the first-time you clone the repository in your build environment,
please run:

```bash
git clone https://github.com/awslabs/aws-deployment-framework
```

If you cloned it before, you do not need to clone it again.

### 3.2. Checkout Specific Version

Before we continue, make sure you navigate into the cloned repository:

```bash
cd aws-deployment-framework
```

By default, if you clone a repository, it checks out the main branch of the
repository.
It is strongly recommended to checkout the tag of the version you would like to
deploy. This makes it easier to investigate potential issues later on.

First we need to update our local copy and fetch the available versions:

```bash
git fetch --verbose --tags
```

Select the version you would like to deploy from the returned list of versions.
You can checkout a specific version by running:

```bash
git checkout ${version_tag_goes_here}

# For example:
git checkout v4.0.0
```

### 3.3. Update Makefile

Before we continue, we need to make sure we have the latest build script.

Update the build script (Makefile) to the latest version by running:

```bash
make update_makefile
```

If this throws an error, the specific version of ADF you are trying to use
might not support this command yet. In that this case, run:

```bash
RAW_ADF_URL=https://raw.githubusercontent.com/awslabs/aws-deployment-framework
curl -fsSL \
    "${RAW_ADF_URL}/make/latest/Makefile" \
    -o ./Makefile.new
mv ./Makefile.new ./Makefile
```

Make sure to run `make clean` next.

### 3.4. Build ADF

Build the ADF version with this command next:

```bash
make
```

If this fails, run `make clean` first and try again.

### 3.5. Notes on a First-Time Deployment

If you are deploying ADF for the first time, it is recommended to read this
section carefully and determine which parameters are required for your specific
use-case.

For example, if you have no AWS Organization or dedicated deployment account
yet, you can enter an account name and email address and ADF will create you
an AWS Organization, the deployment organization unit (OU), along with an
AWS Account that will be used to house deployment pipelines throughout your
Organization.

If you already have an AWS Account you want to use as your deployment
account you can specify its Account ID in the parameter
`DeploymentAccountId` and leave the `DeploymentAccountName` plus
`DeploymentAccountEmail` empty.

**AWS Control Tower-specific Note:**
If you use AWS Control Tower, we recommend to create the deployment AWS
Account via the account vending feature of AWS Control Tower.

It is **MANDATORY**, that your designated deployment AWS Account resides in
the `deployment` (case-sensitive!) OU. This cannot be changed currently.
Also make sure there is only one AWS Account in the deployment organization
unit. Without one, or with more than one the ADF deployment will fail!

The `DeploymentAccountMainRegion` parameter asks for the region that
will host your deployment pipelines and would-be considered your main AWS
region.

In the `DeploymentAccountTargetRegions` section of the parameters
enter a list of AWS Regions that you might want to deploy your resources
or applications into via AWS CodePipeline *(this can be updated later)*.

When deploying ADF for the first time, part of the installation process will
automatically create an AWS CodeCommit repository in the management AWS Account
within the `us-east-1` or `cn-north-1` region. It will also make the initial commit to the
default branch of this repository with a default set of examples that act as a
starting point to help define the AWS Account bootstrapping processes for your
Organization.

Part of the questions that follow will end up in the initial commit into the
repository. These are passed directly the `adfconfig.yml` file prior to it
being committed.

### 3.6. Notes on Updating ADF

ADF releases follow the [semantic version number schems](https://semver.org/).
This implies that breaking changes would require a major version upgrade.
Hence if you upgrade from `2.x` to `3.x`, it is recommended to check the
[release notes](https://github.com/awslabs/aws-deployment-framework/releases)
for details and the breaking changes that it introduced.

### 3.7. Deploy ADF

Next, to deploy ADF, run:

```bash
make deploy
```

This process will raise several questions, please use the documentation below
to determine what to answer for each.

Once you deployed ADF this way, it will ask you to save the configuration.
It is recommended to do so and store the `samconfig.toml` file that it
generates in a Wiki or repository. The next time you need to perform an update
you can rely on that configuration file to use the same settings as configured
with the last deployment.

If this is the first time you deploy using this method, but have an existing
ADF installation. It is recommended to ensure that the values specified reflect
what is installed/in use at the moment.
To gather the values, you can either find them in the
`aws-deployment-framework-bootstrap` repository in the `adfconfig.yml`
file. Or by looking up the values that were specified the last time ADF got
installed/updated via the CloudFormation template parameters of the
`serverlessrepo-aws-deployment-framework` stack in `us-east-1` or `cn-north-1`.

#### Stack Name

Recommended value to use: `serverlessrepo-aws-deployment-framework`

**Explanation:**
This defines the name of the stack with which ADF is deployed
in AWS CloudFormation. In theory, you can customize the stack name.
However, in case of updates of existing installations, you should use the same
name as used before. Otherwise it will attempt to deploy a separate stack aside
of the original one, which will result in a failure.

If you deployed ADF v3.2.0 or earlier and you are about to upgrade that, the
name that it used to deploy is the recommended value stated above.

#### AWS Region

Value to use depends on the AWS partition it is deployed to:

- For the AWS partition (most common), use; `us-east-1`
- For the US-Gov partition, use: `us-gov-west-1`
- For the China partition, use `cn-north-1`

**Explanation:**
ADF needs to be deployed in the region where the control plane of the
AWS Organizations service is hosted. Choose one of the above options based on
the partition you deploy ADF to.

This does not need to be the same region as you are running the development
environment from with Cloud9 for example. Nor does this have to be the same
region as where all the pipelines will be created by ADF. This later region
is configured at a later stage.

#### Parameter CrossAccountAccessRoleName

Default value: `OrganizationAccountAccessRole`

If your AWS Organization is managed via AWS Control Tower, specify
`AWSControlTowerExecution` instead. You can find more information on [using
AWS Control Tower and ADF here](#compatibility-with-aws-control-tower).

**Explanation:**
This role is used to deploy the resources for cross-account management by ADF
initially.

The name of the IAM Role that ADF will use to access other AWS Accounts within
your Organization to create and update base CloudFormation stacks.

This role must exist in all AWS accounts within your Organization that you
intend to use ADF with. When creating new AWS Accounts via AWS Organizations
you can define an initial role that is created on the account, that role name
should be standardized and can be used as this initial cross-account access
role.

*This is not required when performing an update between versions of ADF.*

Please note that changing this value does not change the configured role in an
existing ADF installation. Please update the role to use in the `adfconfig.yml`
file instead, as documented in the [adfconfig section in the Admin
Guide](./admin-guide.md#adfconfig).

#### Parameter MainNotificationEndpoint

Optional, default value: (empty)

Example: `jane@example.com`

**Explanation:**
This allows you to configure the main notification endpoint that should be
informed in case the ADF bootstrapping pipeline failed on the management
account.

*This is not required when performing an update between versions of ADF.*

Please note that changing this value does not change the configured value in an
existing ADF installation. Please update the value to use in the `adfconfig.yml`
file instead, as documented in the [adfconfig section in the Admin
Guide](./admin-guide.md#adfconfig).

#### Parameter DeploymentAccountName

Optional, default value: (empty)

Only required upon first-install, if you want ADF to create a new
deployment account for you. If you specify this, along with the
DeploymentAccountId, it will use the existing deployment account instead
and ignore this setting.

Example: `deployment`

**Explanation:**
The Name of the centralized Deployment Account.
If you have an existing account you wish to use as the deployment account,
insert the name of the AWS account here.

*This is not required when performing an update between versions of ADF.*
*Only supported when installing ADF for the first time.*

Please note that changing this value does not change the account name in an
existing ADF installation.

#### Parameter DeploymentAccountEmailAddress

Optional, default value: (empty)

Example: `jane@example.com`

Only required upon first-install, if you want ADF to create a new
deployment account for you. If you specify this, along with the
DeploymentAccountId, it will use the existing deployment account instead
and ignore this setting.

**Explanation:**
The email address associated with the deployment account,
If you have an existing account you wish to use as the deployment account,
insert the email address of the AWS account here.

*This is not required when performing an update between versions of ADF.*
*Only supported when installing ADF for the first time.*

Please note that changing this value does not change the account email in an
existing ADF installation.

#### Parameter DeploymentAccountAlias

Optional, default value: (empty)

Example: `deployment`

**Explanation:**
The Alias of the deployment account. The account alias is a globally unique
name for an account that enable things such as custom login URLs. Read more
[here](https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html#AboutAccountAlias).

*This is not required when performing an update between versions of ADF.*
*Only supported when installing ADF for the first time.*

Please note that changing this value does not change the account email in an
existing ADF installation.

#### Parameter DeploymentAccountId

Optional, default value: (empty)

Example: `123456789012`

Only required upon updates or a first installation if you want ADF to use an
existing deployment account.

**Explanation:**
The AWS Account number of the **existing** deployment account, only required
if an existing account should be used.

A deployment account will be created if this value is omitted.

Please note that changing this value does not change the account to use in an
existing ADF installation.

#### Parameter DeploymentAccountMainRegion

Required, no default value.

Example: `eu-west-1`

**Explanation:**
The AWS region that will centrally hold all AWS CodePipeline Pipelines.
Pipeline deployments can still span multiple regions. However, they are still
stored and viewed from a single region perspective.
This region is considered your default ADF AWS Region.

Please note that changing this value does not change the configured region in
an existing ADF installation. You need to remove and reinstall ADF to change
the main region.

#### Parameter DeploymentAccountTargetRegions

Optional, default value: (empty)

Example: `eu-central-1,us-east-1`

**Explanation:**
An optional comma-separated list of regions that you may want to deploy
resources *(Applications, CloudFormation etc)* into via AWS CodePipeline.
This can always be updated later via the `adfconfig.yml` file.

You don't need to include the main region in this list. For example, if you
use the example values for the default region and target regions, it will allow
pipelines to deploy to `eu-west-1`, `eu-central-`, `cn-north-1` and `us-east-1`.

*This is not required when performing an update between versions of ADF.*
*Only supported when installing ADF for the first time.

Please note that changing this value does not change the configured regions in
an existing ADF installation. Please update the target regions to use in the
`adfconfig.yml` file instead, as documented in the [adfconfig section in the
Admin Guide](./admin-guide.md#adfconfig).

#### Parameter ProtectedOUs

Optional, default value: (empty)

Example: `ou-123,ou-234`

**Explanation:**
An optional comma-separated list of Organization Unit identifiers that you may
want to protect against having bootstrap stacks applied.

*This is not required when performing an update between versions of ADF.*
*Only supported when installing ADF for the first time.

Please note that changing this value does not change the configured protected
OUs in an existing ADF installation.
Please update the configuration to use in the `adfconfig.yml`
file instead, as documented in the [adfconfig section in the Admin
Guide](./admin-guide.md#adfconfig).

#### Parameter LogLevel

Optional, default value: `INFO`

Example: `DEBUG`
Valid options are: `DEBUG`, `INFO`, `WARN`, `ERROR`, and `CRITICAL`.

**Explanation:**
At what Log Level the ADF should operate, default is INFO.

#### Confirm changes before deploy

Recommended: `Yes`

**Explanation:**
It is recommended to answer with `Yes` here.
This allows you to check if the change set that is created does not introduce
any breaking changes before it is executed.

#### Disable rollback

Recommended: `No`

**Explanation:**
It is recommended to answer with `No` here.
Named resources like the AWS Lambda Layer cannot be updated if rollback is
disabled. However, disabling rollback could be useful if you are experiencing
issues and you want to investigate.

#### Save arguments to configuration file

Recommended: `Yes`

**Explanation:**
It is recommended to answer with `Yes` here.
This will save answers for these questions to the `samconfig.toml`
configuration file.
It is recommended to store the `samconfig.toml` file in a Wiki or repository.
The next time you need to perform an update you can rely on that configuration
file to use the same settings as configured with the last deployment.

#### SAM configuration file

Recommended and default value: `samconfig.toml`

**Explanation:**
You are allowed to change this to `samconfig.yml` or `samconfig.yaml`.
Any other name is not recommended, as the deployment script would need to know
where to find the file. If you insist on using a specific file, please rename
it after and before you use the build and deploy steps.

#### SAM configuration environment

Default value: `default`

**Explanation:**
You are allowed to change this, this is especially useful if you deploy ADF to
multiple environments. Keeping the configuration together in a single file.

**Please note:** This is the last question, once you provided the answer it
will continue to upload the assets and build the CloudFormation change-set.

## What happens next?

Once the **make deploy** command succeeds, the base AWS Deployment Framework
[CloudFormation stack](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks)
is created.

This stack contains a few notable resources such as:

- an [AWS CodeCommit
  Repository](https://console.aws.amazon.com/codesuite/codecommit/repositories/aws-deployment-framework-bootstrap/browse?region=us-east-1)
- along with an associated [AWS CodeBuild
  Project](https://console.aws.amazon.com/codesuite/codebuild/projects/aws-deployment-framework-base-templates/history?region=us-east-1)
- and an [AWS CodePipeline
Pipeline](https://console.aws.amazon.com/codesuite/codepipeline/pipelines/aws-deployment-framework-bootstrap-pipeline/view?region=us-east-1)

The CodeCommit Repository will have its first commit made to it automatically
in the installation process. This is a starting point for using ADF and helps
define the bootstrap process for your AWS ecosystem.

If you updated ADF, it will create a pull request to the main branch on the
same repository instead.

Once the commits land in the main branch, CodePipeline will kick off the AWS
CodeBuild Project to sync the content of the repository with Amazon S3 and
bootstrap the AWS Accounts where required.

It is recommended to go through [the steps how ADF handles AWS Account
provisioning as documented in the admin
guide](./admin-guide.md#account-provisioning).

If you updated ADF, instead of the following steps,
follow the steps described in the [admin guide on updating
ADF](./admin-guide.md#updating-between-versions).

For first-time deployments, the process that deploys ADF continues
automatically in the background, to follow its progress:

1. Please navigate to the AWS Console in the AWS Management account.
   As the stack `serverlessrepo-aws-deployment-framework` completes you can now
   open AWS CodePipeline from within the management account in `us-east-1` or 
   `cn-north-1` and see that there is an initial pipeline execution that started.

   Upon first installation, this pipeline might fail to fetch the source
   code from the repository. Click the retry failed action button to try again.

   When ADF is deployed for the first-time, it will make the initial commit
   with the skeleton structure of the `aws-deployment-framework-bootstrap`
   CodeCommit repository.

   From that initial commit, you can clone the repository to your local
   environment and make the changes required to define your desired base stacks
   via AWS CloudFormation Templates, Service Control Policies or Tagging
   Policies.

2. As part of the AWS CodePipeline Execution from the previous step, the
   account provisioner component will run *(in CodeBuild)*.

   OPTION 2.1: ONLY applies when requesting the creation of a NEW deployment
   account AND when using ADF for vending AWS Accounts.

    - If you let ADF create a new deployment account for you
      *(by not giving a pre-existing account id for the deployment account
      at the time of ADF deployment)*,
      then ADF will handle creating and moving this account automatically into
      the deployment OU.

   OPTION 2.2: ONLY applies when reusing a pre-created deployment account
   AND when using ADF for vending AWS Accounts.

    - If you are using a pre-existing deployment account, ADF will
      move the account into the deployment OU automatically.
      It will also configure your deployment account into a `.yml` file
      within the `adf-accounts` folder.

   OPTION 2.3: ONLY applies when reusing a pre-existing deployment account
   AND when using AWS Control Tower for vending AWS Accounts

    - Ensure that the AWS Control Tower-created deployment AWS Account
      resides in the OU `deployment` (case-sensitive!).

   Regardless of the option taken above, after AWS Account creation, you should
   see an [AWS Step Functions](https://aws.amazon.com/step-functions/) run
   that started the bootstrap process for the deployment account. You can view
   the progress of this in the management account in the AWS Step Functions
   console for the step function `AccountBootstrappingStateMachine-` in the
   `us-east-1` or `cn-north-1` region.

3. Once the Step Function has completed, switch roles over to the newly
   bootstrapped deployment account in the region you defined as your main
   region at ADF deployment time.

   An AWS CodeCommit repository will have been created and will contain the
   initial skeleton structure committed which serves as a starting point for
   defining your pipelines throughout your organization.

   Before defining pipelines, you will most likely want to create more AWS
   accounts and build out your Organization. Bootstrap further accounts by
   moving them into the OU that corresponds to their purpose.

   At this point you can follow the [sample guide](./samples-guide.md) to get
   started with the samples included in this repository which will show in
   detail how pipelines function in ADF.

   **Note** Each account you reference in your `deployment_map.yml` must be
   bootstrapped into an OU prior to adding it to a pipeline.
