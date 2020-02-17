# Types Guide

Types can be defined at the top level or at a stage level of a pipeline to structure the source, build, test, approval, deploy or invoke actions. Types defined in the stage of a pipeline override a default type that was defined at a top level. Types are the basic building blocks of the ADF pipeline creation process and allow for flexibility and abstraction over AWS CodePipeline Providers and Actions.

## Source

```yaml
default_providers:
  source:
    provider: codecommit|github|s3
    properties: ...
```

#### Properties

- **codecommit**
  - account_id - *(String)* **(required)**
    > The AWS Account ID where the Source Repository is located, if the repository does not exist it will be created via AWS CloudFormation on the source account along with the associated cross account CloudWatch event action to trigger the pipeline.
  - repository - *(String)*
    > The AWS CodeCommit repository name. defaults to the same name as the pipeline.
  - branch - *(String)*
    > The Branch on the CodeCommit repository to use to trigger this specific pipeline. Defaults to master.
  - poll_for_changes - *(Boolean)*
    > If CodePipeline should poll the repository for changes, defaults to false in favor of CloudWatch events.
- **github**
  - repository - *(String)* **(required)**
    > The GitHub repository name.
  - owner - *(String)* **(required)**
    > The Owner of the GitHub repository.
  - oauth_token_path - *(String)* **(required)**
    > The oauth token path in AWS Secrets Manager on the Deployment Account that holds the GitHub oAuth token used to create the Webhook as part of the pipeline.
  - json_field - *(String)* **(required)**
    > The name of the JSON key in the object that is stored in AWS Secrets Manager that holds the oAuth Token.
  - branch - *(String)*
    > The Branch on the GitHub repository to use to trigger this specific pipeline. Defaults to master.
- **s3**
  - account_id - *(String)* **(required)**
    > The AWS Account ID where the source S3 Bucket is located.
  - bucket_name - *(String)* **(required)**
    > The Name of the S3 Bucket that will be the source of the pipeline.
  - object_key - *(String)* **(required)**
    > The Specific Object within the bucket that will trigger the pipeline execution.

## Build

```yaml
default_providers:
  build:
    provider: codebuild|jenkins
    enabled: False # If you wish to disable the build stage within a pipeline, defaults to True.
    properties: ...
```

#### Properties

- **codebuild**
  - image *(String)*
    > The Image that the AWS CodeBuild will use. Images can be found [here](https://docs.aws.amazon.com/cdk/api/latest/docs/@aws-cdk_aws-codebuild.LinuxBuildImage.html). Defaults to UBUNTU_14_04_PYTHON_3_7_1. Image can also take an object that contains a property key of *repository_arn* which is the repository ARN of an ECR repository on the deloyment account within the main deployment region. This allows your pipeline to consume a custom image if required. Along with *repository_arn*, we also support a *tag* key which can be used to define which image should be used (defaults to *latest*).
  - size *(String)* **(small|medium|large)**
    > The Compute type to use for the build, types can be found [here](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-compute-types.html). Defaults to *small*.
  - environment_variables *(Object)*
    > Any Environment Variables you wish to be available within the build stage for this pipeline. These are to be passed in as Key/Value pairs.
  - role *(String)*
    > If you wish to pass a custom IAM Role to use for the Build stage of this pipeline. Defaults to *adf-codebuild-role*.
  - timeout *(Number)*
    > If you wish to define a custom timeout for the Build stage. Defaults to 20 minutes.
  - privileged *(Boolean)*
    > If you plan to use this build project to build Docker images and the specified build environment is not provided by CodeBuild with Docker support, set Privileged to True. Otherwise, all associated builds that attempt to interact with the Docker daemon fail. Defaults to False.
  - spec_inline *(String)*
    > If you wish to pass in a custom inline Buildspec as a string for the CodeBuild Project which would override any buildspec.yml file. Read more [here](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html#build-spec-ref-example). Defaults to None.
  - spec_filename *(String)*
    > If you wish to pass in a custom Buildspec file that is within the repository. This is useful for custom deploy type actions where CodeBuild will perform the execution of the commands. Defaults to the buildspec.yml within the repository.

- **jenkins** ([Jenkins Plugin](https://wiki.jenkins.io/display/JENKINS/AWS+CodePipeline+Plugin))
  - project_name *(String)* **(required)**
    > The Project name in Jenkins used for this Build.
  - server_url *(String)* **(required)**
    > The Server URL of your Jenkins Instance.
  - provider_name *(String)* **(required)**
    > The Provider name that was setup in the Jenkins Plugin for AWS CodePipeline.

## Approval

```yaml
provider: approval
properties: ...
```

#### Properties

- **approval**
  - message *(String)*
      > The Message you would like to include as part of the Approval stage.
  - notification_endpoint *(String)*
      > An email or slack channel *(see docs)* that you would like to send the notification to.
  - sns_topic_arn *(String)*
      > Any SNS Topic ARN you would like to receive a notification as part of the Approval stage stage.

## Deploy

```yaml
default_providers:
  deploy:
    provider: cloudformation|codedeploy|s3|service_catalog|codebuild|lambda
    properties: ...
```

#### Properties

- **cloudformation**
  - stack_name - *(String)*
      > The name of the CloudFormation Stack.
  - template_filename - *(String)*
      > The name of the CloudFormation Template to execute. Defaults to template.yml.
  - root_dir - *(String)*
      > The root directory in which the CloudFormation template and params directory reside. Example, when the CloudFormation template is stored in 'infra/custom_template.yml' and parameter files in the 'infra/params' directory, set template_filename to 'custom_template.yml' and root_dir to 'infra'. Defaults to '' (empty string), root of source repository or input artifact.
  - role - *(String)*
      > The role you would like to use on the target AWS account to execute the CloudFormtion action.
  - action - *(String)*
      > The CloudFormation action type you wish to use for this specific pipeline or stage. For more information on actions, see [here](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-action-reference.html#w2ab1c13c13b9).
  - outputs - *(String)*
      > The outputs from the CloudFormation Stack creation. Required if you are using Parameter Overrides as part of the pipeline.
  - change_set_approval - *(Boolean)* **(Stage Level Only)**
      > If the stage should insert a manual approval stage between the creation of the change set and the execution of it.
  - param_overrides - *(List of Objects)* **(Stage Level Only)**
    - inputs *(String)*
      > The input you want to pass into this stage to take a parameter override from.
    - param *(String)*
      > The name of the Parameter you want to override in the specific stage.
    - key_name *(String)*
      > The Key name from the stack output you wish to use as input in this stage.


- **codedeploy**
  - application_name *(String)* **(required)**
    > The name of the CodeDeploy Application you want to use for this deployment.
  - deployment_group_name *(String)* **(required)**
    > The name of the Deployment Group you want to use for this deployment.
  - role - *(String)*
      > The role you would like to use on the target AWS account to execute the CodeDeploy action.

- **s3**
  - bucket_name - *(String)* **(required)**
    > The Name of the S3 Bucket that will be the source of the pipeline.
  - object_key - *(String)* **(required)**
    > The Specific Object within the bucket that will trigger the pipeline execution.
  - extract - *(Boolean)*
    > If CodePipeline should extract the contents of the Object when it deploys it.
  - role - *(String)*
      > The role you would like to use for this action.

- **service_catalog**
  - product_id - *(String)* **(required)**
    > What is the Product ID of the Service Catalog Product to Deploy.
  - configuration_file_path - *(String)*
    > If you wish to pass a custom path to the configuration file path. Defaults to the account-name_region.json pattern used for CloudFormation Parameter files. 

- **lambda**
  - function_name *(String)* **(required)**
      > The name of the Lambda Function to invoke.
  - input *(String)*
      > An Object to pass into the Function as input. This input will be object stringified.
