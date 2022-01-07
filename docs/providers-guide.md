# Providers Guide

Provider types and their properties can be defined as default config for a
pipeline. But also at the stage level of a pipeline to structure the source,
build, test, approval, deploy or invoke actions.

Provider types and properties defined in the stage of a pipeline override the
default type that was defined for that pipeline.
Provider types are the basic building blocks of the ADF pipeline creation
process and allow for flexibility and abstraction over AWS CodePipeline
Providers and Actions.

## Index

- [Source](#source)
  - [CodeCommit](#codecommit)
  - [GitHub](#github)
  - [S3](#s3)
  - [CodeStar](#codestar)
- [Build](#build)
  - [CodeBuild](#codebuild)
  - [Jenkins](#jenkins)
- [Deploy](#deploy)
  - [Approval](#approval)
  - [CodeBuild](#codebuild-1)
  - [CodeDeploy](#codedeploy)
  - [CloudFormation](#cloudformation)
  - [Lambda](#lambda)
  - [Service Catalog](#service-catalog)
  - [S3](#s3-1)

## Source

```yaml
default_providers:
  source:
    provider: codecommit|github|s3|codestar
    properties:
      # All provider specific properties go here.
```

### CodeCommit

Use CodeCommit as a source to trigger your pipeline.
The repository can also be hosted in another account.

Provider type: `codecommit`.

#### Properties

- *account_id* - *(String)* **(required)**
  > The AWS Account ID where the Source Repository is located, if the
  > repository does not exist it will be created via AWS CloudFormation on the
  > source account along with the associated cross account CloudWatch event
  > action to trigger the pipeline.
- *repository* - *(String)* defaults to name of the pipeline.
  > The AWS CodeCommit repository name.
- *branch* - *(String)* default to configured [adfconfig.yml: config/scm/default-scm-branch](./admin-guide.md#adfconfig).
  > The Branch on the CodeCommit repository to use to trigger this specific
  > pipeline.
- *poll_for_changes* - *(Boolean)* default: `False`.
  > If CodePipeline should poll the repository for changes, defaults to
  > False in favor of Amazon EventBridge events.
  >
  > As the name implies, when polling for changes it will check the
  > repository for updates every minute or so. This will show up as actions in
  > CloudTrail.
  >
  > By default, it will not poll for changes but use the event triggered by
  > CodeCommit when an update to the repository took place instead.
- *owner* - *(String)* default: `AWS`.
  > Can be either `AWS` *(default)*, `ThirdParty`, or `Custom`.
  > Further information on the use of the owner attribute can be found in the
  > [CodePipeline documentation](https://docs.aws.amazon.com/codepipeline/latest/APIReference/API_ActionTypeId.html).
- *role* - *(String)* default ADF managed role.
  > The role to use to fetch the contents of the CodeCommit repository.
  > Only specify when you need a specific role to access it. By default ADF
  > will use its own role to access it instead.
- *trigger_on_changes* - *(Boolean)* default: `True`.
  > Whether CodePipeline should release a change and trigger the pipeline.
  > When set to False, you either need to trigger the pipeline manually,
  > through a schedule, or through the completion of another pipeline.
  >
  > This disables the triggering of changes all together when set to False.
  > In other words, when you don't want to rely on polling or event
  > based triggers of changes pushed into the repository.
  >
  > By default, it will trigger on changes using the event triggered by
  > CodeCommit when an update to the repository took place.
- *output_artifact_format* - *(String)* default: `CODE_ZIP`
  > The output artifact format. Values can be either CODEBUILD_CLONE_REF or CODE_ZIP. If unspecified, the default is CODE_ZIP.
  > If you are using CODEBUILD_CLONE_REF, you need to ensure that the IAM role passed in via the *role* property has the CodeCommit:GitPull permission. 
  > NB: The CODEBUILD_CLONE_REF value can only be used by CodeBuild downstream actions. 

### GitHub

Use GitHub as a source to trigger your pipeline.
The repository can also be hosted in another account.

Provider type: `github`.

#### Properties

- *repository* - *(String)* defaults to name of the pipeline.
  > The GitHub repository name.
  > For example, for the ADF repository it would be:
  > `aws-deployment-framework`.
- *branch* - *(String)* default to configured [adfconfig.yml: config/scm/default-scm-branch](./admin-guide.md#adfconfig).
  > The Branch on the GitHub repository to use to trigger this specific
  > pipeline.
- *owner* - *(String)* **(required)**
  > The name of the GitHub user or organization who owns the GitHub repository.
  > For example, for the ADF repository that would be: `awslabs`.
- *oauth_token_path* - *(String)* **(required)**
  > The OAuth token path in AWS Secrets Manager on the Deployment Account that
  > holds the GitHub OAuth token used to create the web hook as part of the
  > pipeline. Read the CodePipeline documentation for more
  > [information on configuring GitHub OAuth](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-GitHub.html#action-reference-GitHub-auth).
- *json_field* - *(String)* **(required)**
  > The name of the JSON key in the object that is stored in AWS Secrets
  > Manager that holds the OAuth Token.
- *trigger_on_changes* - *(Boolean)* default: `True`.
  > Whether CodePipeline should release a change and trigger the pipeline.
  > When set to False, you either need to trigger the pipeline manually,
  > through a schedule, or through the completion of another pipeline.
  >
  > This disables the triggering of changes when set to False.
  > It will not deploy the web hook that GitHub would otherwise use to
  > trigger the pipeline on changes.
  >
  > By default, it will trigger deploy the web hook and trigger on changes
  > using web hook call executed by GitHub.

### S3

S3 can use used as the source for a pipeline too.

Please note: you can use S3 as a source and deployment provider. The properties
that are available are slightly different.

The role used to fetch the object from the S3 bucket is:
`arn:aws:iam::${source_account_id}:role/adf-codecommit-role`.

Provider type: `s3`.

#### Properties

- *account_id* - *(String)* **(required)**
  > The AWS Account ID where the source S3 Bucket is located.
- *bucket_name* - *(String)* **(required)**
  > The Name of the S3 Bucket that will be the source of the pipeline.
- *object_key* - *(String)* **(required)**
  > The Specific Object within the bucket that will trigger the pipeline
  > execution.
- *trigger_on_changes* - *(Boolean)* default: `True`.
  > Whether CodePipeline should release a change and trigger the pipeline
  > if a change was detected in the S3 object.
  >
  > When set to False, you either need to trigger the pipeline manually,
  > through a schedule, or through the completion of another pipeline.
  >
  > By default, it will trigger on changes using the polling mechanism
  > of CodePipeline. Monitoring the S3 object so it can trigger a release
  > when an update took place.

### CodeStar

Use CodeStar as a source to trigger your pipeline.  The source action retrieves code changes when a pipeline is manually executed or when a webhook event is sent from the source provider. CodeStar Connections currently supports the following third-party repositories:

- Bitbucket
- GitHub and GitHub Enterprise Cloud
- GitHub Enterprise Server

The AWS CodeStar connection needs to already exist and be in the "Available" Status. To use the AWS CodeStar Connection with ADF, its arn needs to be stored in AWS Systems Manager Parameter Store in the deployment account's main region (see details below). Read the CodePipeline documentation for more [information on how to setup the connection](https://docs.aws.amazon.com/dtconsole/latest/userguide/getting-started-connections.html).

Provider type: `codestar`.

#### Properties

- *repository* - *(String)* defaults to name of the pipeline.
  > The CodeStar repository name.
  > For example, for the ADF repository it would be:
  > `aws-deployment-framework`.
- *branch* - *(String)* default to configured [adfconfig.yml: config/scm/default-scm-branch](./admin-guide.md#adfconfig).
  > The Branch on the third-party repository to use to trigger this specific
  > pipeline.
- *owner* - *(String)* **(required)**
  > The name of the third-party user or organization who owns the third-party repository.
  > For example, for the ADF repository that would be: `awslabs`.
- *codestar_connection_path* - *(String)* **(required)**
  > The CodeStar Connection ARN token path in AWS Systems Manager Parameter Store in the deployment account
  > in the main region that holds the CodeStar Connection ARN that will be used to download the source
  > code and create the web hook as part of the pipeline. Read the CodeStar Connections documentation
  > for more [information](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections.html).

## Build

```yaml
default_providers:
  build:
    provider: codebuild|jenkins
    # Optional: enabled.
    # The build stage is enabled by default.
    # If you wish to disable the build stage within a pipeline, set it to
    # False instead, like this:
    enabled: False
    properties:
      # All provider specific properties go here.
```

### CodeBuild

CodeBuild is the default Build provider.
It will be provided the assets as produced by the source provider.
At the end of the CodeBuild execution, output assets can be configured
such that these can be deployed in the deployment phase.

CodeBuild can also be configured as a deployment provider.
For more information on this, scroll down to [Deploy / CodeBuild](#codebuild-1).
In terms of the properties, the following properties will be usable for running
CodeBuild as a Build and Deploy provider.

Provider type: `codebuild`.

#### Properties

- *image* *(String)* - default: `UBUNTU_14_04_PYTHON_3_7_1`.
  > The Image that the AWS CodeBuild will use.
  > Images can be found [here](https://docs.aws.amazon.com/cdk/api/latest/docs/@aws-cdk_aws-codebuild.LinuxBuildImage.html).
  >
  > Image can also take an object that contains a property key of
  > `repository_arn` which is the repository ARN of an ECR repository on the
  > deployment account within the main deployment region. This allows your
  > pipeline to consume a custom image if required.
  > Along with `repository_arn`, we also support a `tag` key which can be used
  > to define which image should be used (defaults to `latest`).
  > An example of this setup is provided [here](https://github.com/awslabs/aws-deployment-framework/blob/master/docs/user-guide.md#custom-build-images).
  > 
  > Image can also take an object that contains a reference to a
  > public docker hub image with a prefix of `docker-hub://`, such as
  > `docker-hub://bitnami/mongodb`. This allows your pipeline
  > to consume a public docker hub image if required.
  > Along with the docker hub image name, we also support using a tag which can
  > be provided after the docker hub image name such as `docker-hub://bitnami/mongodb:3.6.23`
  > in order to define which image should be used (defaults to `latest`).
- *size* *(String)* **(small|medium|large)** - default: `small`.
  > The Compute type to use for the build, types can be found
  > [here](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-compute-types.html).
- *environment_variables* *(Object)* defaults to empty object.
  > Any Environment Variables you wish to be available within the build stage
  > for this pipeline. These are to be passed in as Key/Value pairs.
  >
  > For example:
  ```yaml
  environment_variables:
    MY_ENV_VAR: some value
    ANOTHER_ENV_VAR: another value
  ```
- *role* *(String)* default: `adf-codebuild-role`.
  > If you wish to pass a custom IAM Role to use for the Build stage of this
  > pipeline. Alternatively, you can change the `adf-codebuild-role` with
  > additional permissions and conditions in the `global-iam.yml` file as
  > documented in the [User Guide](./user-guide.md).
- *timeout* *(Number)* in minutes, default: `20`.
  > If you wish to define a custom timeout for the Build stage.
- *privileged* *(Boolean)* default: `False`.
  > If you plan to use this build project to build Docker images and the
  > specified build environment is not provided by CodeBuild with Docker
  > support, set Privileged to `True`.
  > Otherwise, all associated builds that attempt to interact with the
  > Docker daemon fail.
- *spec_inline* *(String)* defaults to use the Buildspec file instead.
  > If you wish to pass in a custom inline Buildspec as a string for the
  > CodeBuild Project this would override any `buildspec.yml` file.
  > Read more [here](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html#build-spec-ref-example).
  >
  > Note: Either specify the `spec_inline` or the `spec_filename` in the
  > properties block. If both are supplied, the pipeline generator will throw
  > an error instead.
- *spec_filename* *(String)* default: `buildspec.yml`.
  > If you wish to pass in a custom Buildspec file that is within the
  > repository. This is useful for custom deploy type actions where CodeBuild
  > will perform the execution of the commands. Path is relational to the
  > root of the repository, so `build/buidlspec.yml` refers to the
  > `buildspec.yml` stored in the `build` directory of the repository.
  >
  > In case CodeBuild is used as a deployment provider, the default BuildSpec
  > file name is `deployspec.yml` instead. In case you would like to test
  > a given environment using CodeBuild, you can rename it to `testspec.yml`
  > or something similar using this property.
  >
  > Note: Either specify the `spec_inline` or the `spec_filename` in the
  > properties block. If both are supplied, the pipeline generator will throw
  > an error instead.

### Jenkins

Jenkins can be configured as the build provider, where it will be triggered
as part of the CodePipeline deployed by ADF.

To use Jenkins as a Build provider, you will need to install the
[Jenkins Plugin as documented here](https://wiki.jenkins.io/display/JENKINS/AWS+CodePipeline+Plugin).

Provider type: `jenkins`.

#### Properties

- *project_name* *(String)* **(required)**
  > The Project name in Jenkins used for this Build.
- *server_url* *(String)* **(required)**
  > The Server URL of your Jenkins Instance.
- *provider_name* *(String)* **(required)**
  > The Provider name that was setup in the Jenkins Plugin for AWS CodePipeline.

## Deploy

```yaml
default_providers:
  deploy:
    provider: cloudformation|codedeploy|s3|service_catalog|codebuild|lambda
    properties:
      # All provider specific properties go here.
```

### Approval

The approval provider enables you to await further execution until a key
decision maker (either person or automated process) approved
continuation of the deployment.

```yaml
  provider: approval
  properties:
    # All provider specific properties go here.
```

#### Properties

- *message* *(String)* - default: `Approval stage for ${pipeline_name}`.
  > The message you would like to include as part of the approval stage.
- *notification_endpoint* *(String)*
  > An email or slack channel (see [User Guide docs](./user-guide.md)) that you
  > would like to send the notification to.
- *sns_topic_arn* *(String)* - default is no additional SNS notification.
  > A SNS Topic ARN you would like to receive a notification as part of the
  > approval stage.

### CodeBuild

CodeBuild can also be configured as a deployment provider.

However, it cannot be used to target specific accounts or regions.
When you specify a CodeBuild deployment step, the step should not target
multiple accounts or regions.

As the CodeBuild tasks will run inside the deployment account only.
Using the CodeBuild as a deployment step enables you to run integration tests
or deploy using CLI tools instead.

When CodeBuild is also configured as the build provider, it is useful to
specify a different `spec_filename` like `'deployspec.yml'` or
`'testspec.yml'`.

In case you would like to use CodeBuild to target specific accounts or regions,
you will need to make use of the environment variables to pass in the relevant
target information, while keeping the logic to assume into the correct
role, region and account in the Buildspec specification file as configured
by the `spec_filename` property.

Provider type: `codebuild`.

#### Properties

See [Build / CodeBuild properties](#codebuild) above.

### CodeDeploy

Provider type: `codedeploy`.

#### Properties

- *application_name* *(String)* **(required)**
  > The name of the CodeDeploy Application you want to use for this deployment.
- *deployment_group_name* *(String)* **(required)**
  > The name of the Deployment Group you want to use for this deployment.
- *role* - *(String)* default `arn:aws:iam::${target_account_id}:role/adf-cloudformation-role`.
  > The role you would like to use on the target AWS account to execute the
  > CodeDeploy action. The role should allow the CodeDeploy service to assume
  > it. As is [documented in the CodeDeploy service role documentation](https://docs.aws.amazon.com/codedeploy/latest/userguide/getting-started-create-service-role.html).

### CloudFormation

Useful to deploy CloudFormation templates using a specific or ADF generated
IAM Role in the target environment.

When you are using CDK, you can synthesize the CDK code into a CloudFormation
template and target that in this stage to get it deployed. This will ensure
that the code is compiled with least privileges and can only be deployed using
the specific CloudFormation role in the target environment.

CloudFormation is the default action for deployments.

It will fetch the template to deploy from the previous stage its output
artifacts. If you are specific on which files to include in the output
artifacts be sure to include the `params/*.json` files and the CloudFormation
template that you wish to deploy.

Provider type: `cloudformation`.

#### Properties

- *stack_name* - *(String)* default: `${ADF_STACK_PREFIX}${PIPELINE_NAME}`.
  > The name of the CloudFormation Stack to use.
  >
  > The default `ADF_STACK_PREFIX` is `adf-`. This is configurable as part of
  > the `StackPrefix` parameter in the `deployment/global.yml` stack.
  > If the pipeline name is `some-pipeline`, the CloudFormation stack would
  > be named: `adf-some-pipeline` by default. Unless you overwrite the value
  > using this property, in which case it will use the exact value as
  > specified.
  >
  > By setting this to a specific value, you can adopt a stack that was created
  > using CloudFormation before. It can also help to name the stack according
  > to the internal naming convention at your organization.
- *template_filename* - *(String)* default: `template.yml`.
  > The name of the CloudFormation Template file to use.
  > Changing the template file name to use allows you to generate multiple
  > templates, where a specific template is used according to its specific
  > target environment. For example: `template_prod.yml` for production stages.
- *root_dir* - *(String)* default to empty string.
  > The root directory in which the CloudFormation template and `params`
  > directory reside. Example, when the CloudFormation template is stored in
  > `infra/custom_template.yml` and parameter files in the
  > `infra/params` directory, set `template_filename` to
  > `'custom_template.yml'` and `root_dir` to `'infra'`.
  >
  > Defaults to empty string, the root of the source repository or input
  > artifact.
- *role* - *(String)* default `arn:aws:iam::${target_account_id}:role/adf-cloudformation-deployment-role`.
  > The role you would like to use on the target AWS account to execute the
  > CloudFormation action. Ensure that the CloudFormation service should be
  > allowed to assume that role.
- *action* - *(CHANGE_SET_EXECUTE|CHANGE_SET_REPLACE|CREATE_UPDATE|DELETE_ONLY|REPLACE_ON_FAILURE)* default: `CHANGE_SET_EXECUTE`.
  > The CloudFormation action type you wish to use for this specific pipeline
  > or stage. For more information on actions, see the
  > [supported actions of CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-action-reference.html#w2ab1c13c13b9).
- *outputs* - *(String)* **(Required when using Parameter Overrides)** defaults to none.
  > The outputs from the CloudFormation Stack creation. Required if you are
  > using Parameter Overrides as part of the pipeline.
- *change_set_approval* - *(Boolean)* **(Stage Level Only)**
  > If the stage should insert a manual approval stage between the creation of
  > the change set and the execution of it. This is only possible when the
  > target region to deploy to is in the same region as where the deployment
  > pipelines reside. In other words, if the main region is set to `eu-west-1`,
  > the `change_set_approval` can only be set on targets for `eu-west-1`.
  >
  > In case you would like to target other regions, split it in three stages
  > instead. First stage, using `cloudformation` as the deployment provider,
  > with `action` set to `'CHANGE_SET_REPLACE'`. This will create the Change
  > Set, but not execute it. Add a `approval` stage next, and the default
  > `cloudformation` stage after. The latter will create a new change set and
  > execute it accordingly.
- *param_overrides* - *(List of Objects)* **(Stage Level Only)** defaults to none.
  - *inputs* *(String)*
    > The input artifact name you want to pass into this stage to take a
    > parameter override from.
  - *param* *(String)*
    > The name of the CloudFormation Parameter you want to override in the
    > specific stage.
  - *key_name* *(String)*
    > The key name from the stack output that you wish to use as the input
    > in this stage.

### Lambda

Invoke a Lambda function as a deployment step.

Only Lambda functions deployed in the deployment account can be invoked.
Lambda cannot be used to target other accounts or regions.

Provider type: `lambda`.

#### Properties

- *function_name* *(String)* **(required)**
  > The name of the Lambda function to invoke.
  >
  > For example: `myLambdaFunction`.
- *input* *(Object|List|String)* defaults to empty string.
  > An object to pass into the Lambda function as its input event.
  > This input will be object stringified.

### Service Catalog

Service Catalog deployment provider.

The role used to deploy the service catalog is:
`arn:aws:iam::${target_account_id}:role/adf-cloudformation-role`.

Provider type: `service_catalog`.

#### Properties

- *product_id* - *(String)* **(required)**
  > The Product ID of the Service Catalog Product to deploy.
- *configuration_file_path* - *(String)* default: `params/${account-name}_${region}.json`
  > If you wish to pass a custom path to the configuration file path.

### S3

S3 can use used to deploy with too.

S3 cannot be used to target multiple accounts or regions in one stage.
As the `bucket_name` property needs to be defined and these are globally
unique across all AWS accounts. In case you would like to deploy to multiple
accounts you will need to configure multiple stages in the pipeline manually
instead. Where each will target the specific bucket in the target account.

Please note: you can use S3 as a source and deployment provider. The properties
that are available are slightly different.

The role used to upload the object(s) to the S3 bucket is:
`arn:aws:iam::${target_account_id}:role/adf-cloudformation-role`.

Provider type: `s3`.

#### Properties

- *bucket_name* - *(String)* **(required)**
  > The name of the S3 Bucket to deploy to.
- *object_key* - *(String)* **(required)**
  > The object key within the bucket to deploy to.
- *extract* - *(Boolean)* default: `False`.
  > Whether CodePipeline should extract the contents of the object when
  > it deploys it.
- *role* - *(String)* default: `arn:aws:iam::${target_account_id}:role/adf-cloudformation-role`.
  > The role you would like to use for this action.
