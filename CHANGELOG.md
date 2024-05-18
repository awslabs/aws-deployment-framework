# Changelog

ADF releases follow the [Semantic Versioning
specification](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Breaking changes

#### New installer

The dependencies that are bundled by the move to the AWS Cloud Development Kit
(CDK) v2 increased the deployment size of ADF.
Unfortunately it increased the deployment size beyond the limit that is
supported by the Serverless Application Repository (SAR).

Hence a new installation mechanism is required.

Please read the [installation
instructions](https://github.com/awslabs/aws-deployment-framework/blob/master/docs/installation-guide.md)
carefully.

In case you are upgrading an existing installation of ADF, please consider
following the [upgrade steps as defined in the admin
guide](https://github.com/awslabs/aws-deployment-framework/blob/master/docs/admin-guide.md#updating-between-versions).

#### CDK v2

ADF v4.0 is built on the AWS Cloud Development Kit (CDK) v2. Which is an
upgrade to CDK v1 that ADF relied on before.

For most end-users, this change would not have an impact.
If, however, you made customizations to ADF it might require you to upgrade
these customizations to CDK v2 as well.

#### CodeBuild default image

As was written in the [CodeBuild provider
docs](./docs/providers-guide.md#properties-3), it is a best-practice to define
the exact CodeBuild container image you would like to use for each pipeline.

However, in case you rely on the default, in prior ADF releases it would
default to `UBUNTU_14_04_PYTHON_3_7_1`. This container image is no longer
supported. With ADF v4.0, using the CodeBuild provider requires defining the
specific CodeBuild container image to use. This way, it will not fallback to
a default that might be secure today but deprecated in the future.

For each pipeline definition in the deployment maps, the CodeBuild image will
need to be defined. Alternatively, upgrade ADF and check which pipelines failed
to deploy after. Most likely all pipelines already define the CodeBuild image
to use, as the previous default image is [not supported by
AWS CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-available.html#deprecated-images).

#### ADF Parameters in AWS Systems Manager Parameter Store

Some of the parameters stored by ADF in AWS Systems Manager Parameter Store
were located at the root of the Parameter Store. This made it hard to maintain
and restrict access to the limited set of ADF specific parameters.

With ADF v4.0, the parameters used by ADF are located under the `/adf/` prefix.
For example, `/adf/deployment_account_id`.

If an application or customization to ADF relies on one of these parameters
they will need to be updated to include this prefix. Unless the application
code relies on ADF's ParameterStore class, in that case it will automatically
prefix the `/adf/` to all parameters read or written.

With the changes in the IAM policies, ADF's access is restricted to the `/adf/`
prefix. This, unfortunately implies that old parameters are not deleted when
you update your installation of ADF. There is no cost associated to these
parameters, so you can leave them as is.
Feel free to delete the old parameters.

The parameters that are managed by ADF that got their path changed are:

For the __management account__, in the __AWS Organizations region__
(`us-east-1`, or `us-gov-west-1`):

| Old Parameter Path           | New Parameter Path               |
|------------------------------|----------------------------------|
| `/adf_log_level`             | `/adf/adf_log_level`             |
| `/adf_version`               | `/adf/adf_version`               |
| `/bucket_name`               | `/adf/bucket_name`               |
| `/confit`                    | `/adf/config`                    |
| `/cross_account_access_role` | `/adf/cross_account_access_role` |
| `/deployment_account_id`     | `/adf/deployment_account_id`     |
| `/deployment_account_region` | `/adf/deployment_account_region` |
| `/kms_arn`                   | `/adf/kms_arn`                   |
| `/notification_channel`      | `/adf/notification_channel`      |
| `/organization_id`           | `/adf/organization_id`           |
| `/protected`                 | `/adf/protected`                 |
| `/scp`                       | `/adf/scp`                       |
| `/shared_modules_bucket`     | `/adf/shared_modules_bucket`     |
| `/tagging-policy`            | `/adf/tagging_policy`            |
| `/target_regions`            | `/adf/target_regions`            |

For the __management account__, in __other ADF regions__:

| Old Parameter Path           | New Parameter Path               |
|------------------------------|----------------------------------|
| `/adf_version`               | `/adf/adf_version`               |
| `/bucket_name`               | `/adf/bucket_name`               |
| `/cross_account_access_role` | `/adf/cross_account_access_role` |
| `/deployment_account_id`     | `/adf/deployment_account_id`     |
| `/kms_arn`                   | `/adf/kms_arn`                   |

For the __deployment account__, in __the deployment region__:

| Old Parameter Path           | New Parameter Path                  |
|------------------------------|-------------------------------------|
| `/adf_log_level`             | `/adf/adf_log_level`                |
| `/adf_version`               | `/adf/adf_version`                  |
| `/auto_create_repositories`  | `/adf/scm/auto_create_repositories` |
| `/cross_account_access_role` | `/adf/cross_account_access_role`    |
| `/default_scm_branch`        | `/adf/scm//default_scm_branch`      |
| `/deployment_account_bucket` | `/adf/deployment_account_bucket`    |
| `/master_account_id`         | `/adf/management_account_id`        |
| `/notification_endpoint`     | `/adf/notification_endpoint`        |
| `/notification_type`         | `/adf/notification_type`            |
| `/organization_id`           | `/adf/organization_id`              |

For the __deployment account__, in __other ADF regions__:

| Old Parameter Path           | New Parameter Path               |
|------------------------------|----------------------------------|
| `/adf_log_level`             | `/adf/adf_log_level`             |
| `/adf_version`               | `/adf/adf_version`               |
| `/cross_account_access_role` | `/adf/cross_account_access_role` |
| `/deployment_account_bucket` | `/adf/deployment_account_bucket` |
| `/master_account_id`         | `/adf/management_account_id`     |
| `/notification_endpoint`     | `/adf/notification_endpoint`     |
| `/notification_type`         | `/adf/notification_type`         |
| `/organization_id`           | `/adf/organization_id`           |

For a __target account__, in __each ADF region__:

| Old Parameter Path       | New Parameter Path           |
|--------------------------|------------------------------|
| `/bucket_name`           | `/adf/bucket_name`           |
| `/deployment_account_id` | `/adf/deployment_account_id` |
| `/kms_arn`               | `/adf/kms_arn`               |

#### AWS CodeStar Connections OAuth Token support dropped

ADF v4.0 discontinued the support for the OAuth Token stored in
SSM Parameter Store. As this method is not advised to be used by CodePipeline,
and might leave the OAuth Token accessible to other users of the deployment
account. As this is not a security best practice, ADF v4.0 no longer supports
it.

To upgrade, please read the [Administrator Guide on Using AWS CodeConnections
for Bitbucket, GitHub, or
GitLab](./docs/admin-guide.md#using-aws-codeconnections-for-bitbucket-github-github-enterprise-or-gitlab).

#### AWS CodeStar Connections changed to AWS CodeConnections

The AWS CodeStar Connection service [changed its name to AWS
CodeConnections](https://docs.aws.amazon.com/dtconsole/latest/userguide/rename.html).

If you configured a CodeStar Connection before, you can continue to use that.
You do not need to update the CodeStar policy as defined in the
`aws-deployment-framework-bootstrap/adf-bootstrap/deployment/global-iam.yml`
stack.

However, please update the pipeline definitions in your deployment map files.
The changes you need to make are renaming the source
provider from `codestar` to `codeconnections`.
Also update the `codestar_connection_path` source property to
`codeconnections_param_path`.

Both of these changes can be seen in the following example:

```yaml
pipelines:
  - name: sample-vpc
    default_providers:
      source:
        # provider: codestar
        provider: codeconnections
        properties:
          # codestar_connection_path: /adf/my_connection_arn_param
          codeconnections_param_path: /adf/my_connection_arn_param
```

If you are upgrading from the GitHub OAuth token or otherwise require a new
source code connection, please proceed with the AWS CodeConnections
configuration as defined in the
[Admin Guide - Using AWS CodeConnections for Bitbucket, GitHub, or
GitLab](./docs/admin-guide.md#using-aws-codeconnections-for-bitbucket-github-or-gitlab).

---

## v3.2.0

__Please note__: this update refactored the account creation and pipeline
generation to use Step Functions.  Thereby, the process to track how the update
progresses and how you could validate its operation changed.
Please read [the docs on updating
ADF](https://github.com/awslabs/aws-deployment-framework/blob/3ae94baf6908a6f25177ea21cd2f2e0d3a5b808b/docs/admin-guide.md).

We are thankful to the community that helped enhance ADF.
With this release, we decided to list the contributions per author (listed in
alphabetical order) within each section.  Highlighting the great contributions
and enhancements that were made by them.

### Features

apogorielov:

- Add ability to override the default branch for all source code providers #370.

benbridts:

- Allow top-level keys starting with `x-` or `x_` in deployment maps to add
  support for YAML anchors #347.

dsudduth:

- Fix AWS partition reference, adding support for AWS Gov Cloud #381,
  closes #332.

ivan-aws:

- Add ability to use CodeStar sources in deployment map #312.
- Add support to configure object ACL with S3 put object calls #412.

pozeus:

- Add support for CodeBuild to pull from docker hub #349, requested in #196.

srabidoux:

- Add support for account-specific SCP deployments #395.

stemons:

- Add support for Terraform deployments #397, closes #259, implements #114.

StewartW:

- Add ChatBot support for notifications, lifting the limit on pipelines that
  notify through Slack #367, closes 257, closes 297.
- Add support for pipeline triggers #392, closes #372.
- Add ability to define CodeCommit artifact format #389, closes #387.
- Add deployment waves for targets, removing the manual effort to spread 50
  accounts per stage #358, closes #290, implements #128, closes #296,
  closes #250, closes #427.
- Add support to exclude specific account ids from a target group #358,
  closes #145.

sbkok:

- Add ability to disable trigger on changes for S3/CC/GH source providers #357:
  - Allows starting the pipeline only upon a `completion_trigger` event,
    closes #308.
  - Allows you to disable reacting to the Github webhook, closes #337.
- Add support to change the default branch on ADF bootstrap and pipelines
  repositories #508.
- Add support for CodeBuild to run inside a VPC #517.
- Refactor `generate_params.py` helper, adding support for per parameter/tag
  resolution from specific to least specific params file #559, closes #452,
  closes #294.
- Add support for CodeStar CodeBuild clone ref, allowing to work on git commits
  in CodeBuild in pipelines #563.
- Allow CloudFormation parameter file name configuration per target #565.

### Fixes

benbridts:

- Remove unacceptable characters from CloudFormation Stack names #346.

dependabot:

- Bump ejs from 2.6.1 to 3.1.7 in Fargate node sample application #480.
- Bump express from 4.16.4 to 4.17.3 in Fargate node sample application #555.

javydekoning:

- Fix resource reference in Step Function state machine policy #461,
  closes #460.
- Fix string should be array reference in Event Bridge Rule #456, closes #455.
- Bump Jinja2 and Boto3 versions to 3.1.1 and 1.21.31 respectively #457,
  closes #454.
- Ensure account alias is configured or fail #465, closes #242.
- Fix account file processing and add debug logging #459, closes #458.

mhdaehnert:

- Separate artifact storage bucket for CodePipeline and CodeBuild to improve
  parallel execution #271, closes #270.

Nr18:

- Fix S3 object ownership controls #448, closes #447.
- Fix param overrides functionality to support using the same source #446,
  closes #445.

rickardl:

- Support paginator for parameters and empty descriptions in moved to root
  lambda #273, fixes #272.

tylergohl:

- Add retry for InvalidTemplateError and GenericAccountConfigureError #384,
  closes #383.

StewartW:

- Fix deployment account Step Function time outs #401, closes #400.
- Fix incorrect step name in step function #406.
- Update get account region function to use opted-in regions to #423,
  closes #420.
- Reduce adf-codepipeline-role policy size when ADF deploys to many regions
  #475, closes #474.

sbkok:

- Add missing requirements file for shared python helpers, fixes use of
  `retrieve_organization_accounts.py` helper #352.
- Fix duplicate notification endpoint setup in pipeline generation #362.
- Fix specifying the tag on CodeBuild repository image to use #377,
  closes #374.
- Fix permission to set Support Subscription upon account creation #402,
  closes #379.
- Fix duplicated steps in Account Bootstrap Step Function #414.
- Fix global-iam example comment explaining where it is deployed #421.
- Fix use of correct region for AWS Organizations API depending on the
  partition it runs in #485.
- Fix correct use of build/deploy parameters for CodeBuild provider #489,
  closes #488.
- Fix account processing to be part of our SAR distribution #487.
- Fix Makefile use of find command on macOS #497, closes #473.
- Fix update process to only flag helpers as executable #499.
- Fix correct use of partitions #502.
- Fix use of NodeJS 14 with Standard 5.0 CodeBuild containers #500,
  closes #385.
- Fix MarkupSafe to v2.0.1 as v2.1 breaks compatibility with Jinja2<3.0.0 #498,
  closes #467, closes #441.
- Fix use of separate container image per target #501, closes #382.
- Fix wrapt version dependency #504.
- Fix syncing deployment map files to S3 when needed #506.
- Fix missing permission on cross-account org read-only role #509.
- Fix permission to update termination protection on pipeline stacks #511.
- Fix ADF state machines #514, closes #513.
- Fix updating account alias when needed #515.
- Fix tenacity version dependency #520.
- Fix Step Function input file syncing to upload only when content changed
  #530, part of #518.
- Fix pipeline generation policies #533.
- Fix repository creation permission in pipeline management #536.
- Fix stale pipeline deletion #535.
- Fix account creation wait for bootstrap to complete #537, closes #518.
- Fix initial commit implementation #534.
- Fix account bootstrap on organization unit move #539.
- Fix IAM Tag permissions #545.
- Fix initial commit on new/fresh install #544.
- Fix ADF Config storage, needs to be stored before used the first time #548.
- Fix pipeline regeneration upon account move #550, closes #549.
- Fix syncing to S3 in the root of the bucket #558.
- Fix CodePipeline source account id lookup to support missing account id for
  providers like CodeStar #561.
- Fix CreateRolePolicy permissions on global.yml bootstrap stacks #564.
- Fix clean-up of stale deployment map files in the pipeline bucket #562.
- Fix CodePipeline references to a specific config per stage over a default
  provider config #565.
- Fix executable flags of helper scripts #573.
- Fix CloudFormation permissions to update the pipeline notification SNS topic
  subscriptions #572.
- Fix permissions to enable CodeBuild as a deployment provider #571.
- Fix typos in pipeline management logical id #567.
- Fix generate_params.py pipeline regions lookup #584.
- Fix bootstrapping in non-protected OUs only #590.

### Improvements

benbridts:

- Clean up of protected organization unit error message #353.
- Improvements to the Serverless Application Repository template #343,
  closes #342.

javydekoning:

- Add CloudFormation linting using cfn-lint #466, closes #464.
- Replace Travis with GitHub Actions #481.
- Add YAML linting using yamllint #470, closes #463.
- Fix yamllint findings #482.
- Upgrade to CDK v1.168, pylint v2.13 and others #486.
- Add MegaLint to organize execution of all linters configured #492, part of
  #491.
- Fix linting issues in RDK sample #495.
- Fix editor config linting #516, part of #491.
- Improve docs, add markdown linting, and change master account to management
  account in docs #521, part of #491.
- Improve code and docs by adding CSpell checks to enforce correct spelling
  #574.
- Improve CSpell linter output #578.

Nr18:

- Encrypt SNS topic using ADF's CMK KMS Key #429, closes #422.
- Define CodeCommit description in deployment maps #469, closes #468.

ntwobike:

- Add RDK sample to deploy custom Config rules #451.

skycolangelom:

- Fix retry logic for DescribeRegions while creating new accounts #238,
  rebased and improved in #348.
- Fix deleting default VPC when it is non-empty #238, rebased + improved in
  #348.

StewartW:

- Add pipeline type parameters to enable support for other pipelines in the
  future #285, closes #185.
- Add Bootstrap Repository Pipeline high-level overview documentation from a
  tech perspective #393, closes #211.
- Refactor Account management to use a Step Function #394.
- Reduce number of IAM API calls during cross-account access setup process
  #408.
- Refactor Pipeline management to use a Step Function, added tech diagrams
  #424, closes #211.
- Add in role paths for new account management roles #523.
- Fix MegaLint style error #531.
- Add deployment map source to SSM Params to identify out-of-date pipelines
  #525.
- Add retry logic on pipeline generation RunCDK stage when CodeBuild is
  throttled #580.

sbkok:

- Upgrade urlize from v2.11.2 to v2.11.3 #341.
- Lock down buckets created by ADF, block public access #350.
- Improve ADF version references in the main template #351.
- Upgrade dependencies (CDK to v1.105, Pylint to v2.8.2, SAM CLI to v1.23.0,
  and others) #364.
- Upgrade dependencies (CDK to v1.114, Pylint to v2.9.3, SAM CLI to v1.26.0,
  and others) #376, closes #388.
- Improved error message with accounts yaml read failures #403, closes #213.
- Enable setting the log level when deploying from the SAR + adding a
  troubleshoot ADF guide #409.
- Update docs to state the default branch used as the source #418.
- Change example email domains and account ids #416.
- Update to CDK v1.137, pylint v2.12, and others to latest available #417.
- Upgrade to Python 3.9 #415.
- Add editorconfig to repository #483.
- Refactor line lengths and code style #490.
- Update CDK, use of NodeJS 16 where possible, and CodeBuild Standard 5.0
  images #496, closes #291.
- Only invoke pipeline deletion when needed #510.
- Add reference to Step Function Pipeline Management state machine from
  pipelines CodeBuild execution #512.
- Add retry logic to Step Function Lambda invocations and improved log messages
  #513, closes #371.
- Make consistent use of Id in pipeline management implementation #532.
- Add account creation in-progress retry logic, fixes
  SubscriptionRequiredException #540, closes #519, fixes #366.
- Add retries to account bootstrap process #543, closes #366.
- Update to CDK v1.181.1 and others #553.
- Improve readability of pipeline generation executions in the newly introduced
  pipeline generation state machine #557.
- Improve parameter validation on install/update of ADF, improving
  install/update experience #554.
- Update to CDK v1.182.0 #560.
- Improve adf-pipelines CodeBuild permissions to start state machines
  and optimized CodeBuild machine type #569.
- Add CodeBuild VPC permissions to default permissions to easy provisioning
  pipelines inside VPCs #570.
- Improve policy names in adf-bootstrap example global-iam.yml files to be
  unique #568.
- Improve code readability of CodeBuild class through refactoring #566.
- Update ADF update process and troubleshooting documentation #576.
- Improve CloudFormation error reporting in the
  aws-deployment-framework-bootstrap pipeline #582.
- Reduce number of cross-account access IAM API calls #581.
- Add exponential back-off retries on Enable Cross-Account Access state
  machine #581.
- Refactor and tighten roles used by Enable Cross-Account Access state
  machine #581.
- Do not retry pipeline generation if an account is not found or the deployment
  map is invalid #583.
- Refactor pipeline management pipeline input generation and execution #584.

Many thanks to our community for driving this release. And special thanks to
apogorielov, benbridts, dsudduth, ivan-aws, javydekoning, mhdaehnert, Nr18,
ntwobike, pozeus, rickardl, skycolangelom, srabidoux, stemons, StewartW,
and tylergohl for contributing new features and improvements to ADF!

---

## v3.1.2

### Fixes

- Fix use of the `resolve:` intrinsic function on the first parameter
  in the parameter files, #336.

---

## v3.1.1

### Fixes

- Fixes `timeout` and `environment_variables` to be used when defined in the
  default CodeBuild Deployment provider properties #307, closes #306.
- Fixes intrinsic functions for account_region param files #333, closes #147.
- Fixes use of deployment from source directly when build stage is disabled
  #334, closes #236 and closes #318.

---

## v3.1.0

### Features

- Adds Enterprise Support to account creation process #233, closes #232:
  - ADF will raise a ticket to add the account to an existing AWS support
    subscription when an account is created. As a prerequisite, your
    organization management account must already have enterprise support
    activated.
- Adds nested deployment map support #266 and #328, closes #265:
  - This enables usage of sub directories within the deployment_maps folder.

### Fixes

- Fixes specific role usage to be used in Build and Deploy only #295.
- Corrects removing pipelines anchor in docs #279.
- Fixes CI builds due to isort version mismatch #284.
- Fixes error handling of generate_params intrinsic upload function #277,
  closes #276.
- Fixes spec_inline attribute of CodeBuild in docs #289.
- Fixes provider spec_inline support of CodeBuild in #293.
- Fixes supported list of intrinsic upload path styles, enables usage of s3-url
  and s3-key-only #275, closes #299.
- Fixes create deployment account concurrency failure #287, closes #280.
- Fixes approval stage usage, by limiting specific role usage to Build and
  Deploy steps #295.
- Fixes yarnpkg GPG #313,  closes #325.
- Removes dependency on botocore.vendored.requests #326, closes #324.

### Improvements

- Improves docs on providers and their properties #274.
- Separates pipeline cleanup from input generation script #288.
- Upgrades Python from v3.7 to v3.8 #313.
- Upgrades CodeBuild image from "aws/codebuild/standard:2.0" to
  "aws/codebuild/standard:5.0" #313, closes #267, closes #300.
- Upgrades CDK from v1.32 to v1.88 #313, closes #292.

Many thanks to our community for driving this release. And special thanks to
@StewartW for contributing new features to ADF!

---

## v3.0.6

### Fixes

- Account Alias’ are no longer automatically created as the accounts full name.
- Adding in additional wait time for account creation process (Temporary Fix)

### Improvements

- CDK Version 1.25 -> 1.32
- Adding ability to tag pipelines (example included in docs)
- Adding in CloudFormation:* in global-iam-example.yml for target accounts.

---

## v3.0.5

### Fixes

- Fix CodeBuild use specific image in target stage  #253.
- Fix import references of export to output key #248.
- Fix CodeBuild assume role to generate parameters #247.

### Improvements

- Adds s3-key-only style #249.

---

## v3.0.4

### Fixes

- Fix CloudFormation deployment role generation.
- Fix overwrite of deployment/global-iam.yml #227.
- Fix IAM for retrieve organization accounts helper #229.
- Fix IAM for package transform helper to function #228.
- Version lock missing CDK dependencies #225.

### Improvements

- Add S3-URI and S3-URL as upload path styles #224.
- Allow adf-automation-role policy to grant
  cloudformation:UpdateTerminationProtection #222.

---

## v3.0.3

### Fixes

- Fix CodeCommit usage in pipelines.
- Fix CodeBuild usage in pipelines with correct default values.

---

## v3.0.2 [YANKED]

This release was yanked, as deploying it caused various issues with the default
CodeBuild and CodeCommit pipeline resources. These issues are fixed in v3.0.3.

---

## v3.0.1

### Fixes

- Fixed SCP and Tagging Policy files to use relative paths #212.

---

## v3.0.0

This release is specifically focused two main topics: *Security* and
*Account provisioning*.

### Security

In this release we are limiting default IAM policies to ensure pipeline phases
such as custom deployments or build phases cannot be used to elevate ones own
permissions. To ensure strict separation of concerns and enforce high standards
around IAM we have created two new IAM Role that lives on each AWS Account
within the organization. These role are created in the global.yml
*(base stack)* of each account and are used for the following purposes:

**adf-automation-role:**

> When creating pipelines in ADF there are certain things that are required to
> be setup on multiple different accounts. For example, the source account
> requires a repository on it, and also a CloudWatch event. Previously the
> CodeBuild role would assume the adf-cloudformation-deployment-role in the
> target account and create the required CloudFormation stack. This pattern
> allowed the adf-codebuild-role to much power and thus we have removed this
> link.

This new role (`adf-automation-role`) is assumed by CodeBuild in the
`aws-deployment-framework-pipelines` pipeline exclusively and cannot be
assumed by the standard *(other)* deployment pipelines.

**adf-readonly-automation-role:**

> When CodeBuild runs as part of a standard deployment pipeline
> *(anything other than `aws-deployment-framework-pipelines`)* it uses the
> role: `adf-codebuild-role` by default.
> The `adf-codebuild-role` has access to assume this new role
> (`adf-readonly-automation-role`) on each account within the organization.
> It assumes this role when running certain intrinsic functions
> such as import or resolve which allow values to be retrieved from other
> AWS Accounts within the organization. Previously, CodeBuild would assume the
> adf-cloudformation-deployment-role to retrieve these values which can have
> many actions allowed making it inappropriate to assume.

This change effectively lowers the amount of permissions the default
`adf-codebuild-role` has. Prior to this release, using CodeBuild as a deployment
stage would also default to the `adf-codebuild-role` which would allow the
deployment stage more accesses than intended. From this release onward,
CodeBuild stages will default to the `adf-codebuild-role`. However, since this
role has very limited access, it will most likely require the user to define a
custom role in order to assume and deploy resources into other accounts.

For example, if you wanted to deploy some resources with Terraform, or run
"cdk deploy" you would need to provide an IAM role that has been created which
has the required permissions to do so. For more information on how to create
such as role, see the commented out `adf-custom-deploy-role` in the
`example-global-iam.yml`.

### Account Provisioning

Until this release ADF has not had a streamlined automated way to create and
move AWS accounts into organizational units. With 3.0.0 we are introducing an
account provisioner concept that handles the creation and OU location of AWS
Accounts in a declarative format. As part of the bootstrap repository we have
created a new root folder titled adf-accounts, this folder contains definition
files *(yaml)* that describe AWS accounts along with an assortment of
properties. The bootstrap pipeline automation component (in CodeBuild) will
parse the files and create or move the accounts into their defined state.
This allows for end to end creation, bootstrapping and pipeline generation of
an AWS account *(all from code!)*. For more information on this process and a
breakdown of the file properties and syntax itself see the admin guide
*(also see `readme.md` in the `adf-accounts` folder)*.

### Inter OU Moving of AWS Accounts

Moving accounts between two OU's will now trigger the previous base stack to be
removed and the new base stack aligned with that Organizational Unit to be
applied.

### Tagging Policies

With this release, ADF enables streamlined automation and management of Tagging
Policies via AWS Organizations. Tagging Policies can now be applied to OU's in
the same manner as Service Control Policies could be in prior versions.
Using a tagging-policy.json file in a specific folder of the bootstrap
repository that matches to your organization structure enables the tagging
policy for the specific OU. Read more about how tagging policies work
[here](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
and see the example-tagging-policy.json in the bootstrap repo for a simple
reference.

### Separation of adf-cloudformation-deployment-role IAM Policy

Moving forward we have decided to move the adf-cloudformation-deployment-role
policy out of the global.yml and into a new file called `global-iam.yml`,
this change hopes to simplify and create a separation between the global.yml
which contains resources related to ADF in general as opposed to the new file
(global-iam.yml) which relates to what can and cannot be deployed into the
account that applies that specific base stack. The new global-iam.yml file is
searched for recursively in the same fashion other global.yml or regional.yml
files.

### Other changes

- Resolved #196 - Support for custom CodeBuild images *(You can now use custom
  build images in your build or deploy actions with CodeBuild. See user-guide
  for more information and examples.)*
- Resolved #198 - Parameter Store is no longer used for the state of the
  pipeline definition, this has been moved to S3.
- Resolved #191 - Simple check to determine region is correct when deploying
  from SAR.
- Resolved #189 - Enable flag for build stage bug fixed, now works as intended.
- Resolved #180 - error handling has been fixed to correct this.
- Resolved #178 - ADF Account provisioning is here!
- Resolved #177 - Upgrades will not touch the global-iam.yml file which holds
  the cloudformation-deployment-role-policy.
- Resolved #188 - Removed hard-coded branch name from source account CloudWatch
  event.
- Resolved #148 - Base stack *(iam and bootstrap)* are removed and re-added
  based on inter OU account moves.
- cdk version bumped to 1.2.0
- removed hard coding of master branch on PR event action on source accounts.

### Upgrading from 2.x to 3.x

With the change to 3.0 we have decided to move the bootstrap content
(`templates/scps`) in the bootstrap repository into its own folder
(`adf-bootstrap`). Since the bootstrap folder path is changing from the root of
the repository into the `adf-bootstrap` folder, you will need to move your
existing folder structure (`.yml/scp` files) into the new format. When
deploying ADF 3.x from the SAR a Pull Request will get made against the
bootstrap repository as per normal upgrade process. The 3.0 PR will move the
ADF specific content including the deployment folder into the new structure,
if you have significantly altered the `global/regional.yml` for the deployment
account be sure to adjust this as intended prior to merging it to the main
branch.

If you require to make alterations to the structure of the folders/templates
simply pull the 3.0 branch down and add in your existing folder/OU structure
as desired with the `adf-bootstrap` folder as the new root and push back into
the branch.

With the 3.0 change there is also an `example-global-iam.yml` file that is
included in the root of the `adf-bootstrap` folder. This file should be renamed
to `global-iam.yml` and distributed into the folders/OUs that you intend to
have CloudFormation deploy resources into. This is required in order to define
what actions the role on the target accounts will have access to when deploying
CloudFormation resources via CodePipeline.

Steps to perform for the upgrade process:

- Deploy ADF.
- Once deployed, navigate to CodeCommit, pull down the branch for 3.0.
  In your editor, update your folder organizational structure *(if you have
  one)* into the `adf-bootstrap` folder. *(this folder is the new "root" for
  bootstrapping)*. Ensure you are getting the new content from the deployment
  folder.
- Ensure you are bringing in the new content from the global.yml file in 3.0
  release, the two roles and their associated policies (`adf-automation-role`,
  `adf-readonly-automation-role`).
- Rename the `example-global-iam.yml` to `global-iam.yml` and ensure its policy
  suits your needs and that it is in the correct folder structure that suits
  your organization security requirements. *(this file now holds the policy for
  what CFN can do on target accounts)*
- Push the updated content back to the branch and merge if all looks to be
  correct.
