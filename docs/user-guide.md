# User Guide

- [Deployment Map](#deployment-map)
- [Deploying via Pipelines](#deploying-via-pipelines)
  - [Repositories](#repositories)
  - [BuildSpec](#buildspec)
  - [Parameters](#parameters)
  - [Parameter Injection](#parameter-injection)
  - [Nested Stacks](#nested-stacks)
  - [Deploying Serverless Applications with SAM](#deploying-serverless-applications-with-sam)

## Deployment Map

The deployment_map.yml file lives in the Repository named *aws-deployment-framework-pipelines* on the Deployment Account. This file is responsible for mapping the specific pipelines to their deployment targets and desired pipeline. When creating pipelines in the deployment account, a python file called *generate_pipelines.py* *(see adf-build folder)* will be executed during CodeBuild via CodePipeline. This small piece of code will parse the deployment_map.yml file and assume a role on the master account in the organization. It will then resolve the accounts in the organization unit's specified in the mapping file. It will return the account name and ID for each of the accounts and pass those values in the Jinja2 templating engine along side a template file *(see pipeline_types folder)*. The template of choice is taken from the type property in the mapping file.

The parameters *(params)* you chose to pass into the Jinja2 template are taken directly from the deployment_map.yml file. This allows you to build sensible defaults in your pipeline definitions and pass in only what is required for that specific pipeline creation.

The Deployment map file allows for some unique steps and actions to occur in your pipeline. You can add an approval step to your pipeline by putting a step in your targets definition titled, *'approval'* this will add a manual approval stage at this point in your pipeline.

A basic example of a deployment_map.yml would look like the following *(assumes eu-west-1 and eu-central-1 have been bootstrapped in adfconfig.yml)*:

```yaml
pipelines:
  - name: iam
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111222222
      - NotificationEndpoint: janes_team@doe.com
    targets:
      - path: /security
        regions: eu-west-1
      - approval
      - path: /banking/testing
        regions: eu-central-1


  - name: vpc
    type: github-cloudformation
    regions: [ eu-west-1, eu-central-1 ]
    action: replace_on_failure
    contains_transform: true
    params:
      - SourceAccountId: 8888877777777
      - NotificationEndpoint: channel1
    targets:
      - ou-12341
      - 22222222222
```

In the above example we are creating two pipelines. The first one will deploy from a repository named **iam** that lives in the account **111111222222**. It will use the *cc-cloudformation* [type](#pipeline-types) and deploy in 3 steps. The first stage of the deployment will occur against all AWS Accounts that are in the `/security` Organization unit and be targeted to the `eu-west-1` region. After that, there is a manual approval phase which is denoted by the keyword `approval`. The next step will be the accounts within the `/banking/testing` OU for `eu-central-1` region. By providing a simple path or ou-id without a region definition it will default to the region chosen as the deployment account region in your [adfconfig](./admin-guide/adfconfig.yml). Any failure during the pipeline will cause it to halt.

The second example is a simple example that deploys to an OU using its OU identifier number `ou-12341`. You can chose between a absolute path *(as in the first example)* in your AWS Organization or by specifying the OU ID. The second stage of this pipeline is simply an AWS Account ID. If you have a small amount of accounts or want to one of deploy to a specific account you can use an AWS Account Id if required.

In this second example, we have defined a channel named `channel1` as the *NotificationEndpoint*. By doing this we will have events from this pipeline reported into the Slack channel named *channel`*. In order for this functionality to work as expected please see [Integrating Slack](./admin-guide/integrating-slack).

By default, the above pipelines will use a method of creating a change set and then executing the change set in two actions. Another top level option is to specify `action: replace_on_failure` on a specific pipeline. This changes the pipeline to no longer create a change set and then execute it but rather if the stack exists and is in a failed state *(reported as ROLLBACK_COMPLETE, ROLLBACK_FAILED, CREATE_FAILED, DELETE_FAILED, or UPDATE_ROLLBACK_FAILED)*, AWS CloudFormation deletes the stack and then creates a new stack. If the stack isn't in a failed state, AWS CloudFormation updates it. Use this action to automatically replace failed stacks without recovering or troubleshooting them. *You would typically choose this mode for testing.* You can use any of the action types such as *create_update* defined [here](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-action-reference.html).

You can also run pipelines on a specific schedule, this is common for pipelines that produce some sort of output on a regular basis. For example, creating a new [AMI each week](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-an-ami-ebs.html). To do this specify the cron expression as the input for the *ScheduleExpression* parameter within the pipeline of your choice. You can choose between a *rate* expression or *cron* expression, [read more](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html).

```yaml
  - name: ami-builder
    type: cc-buildonly
    params:
      - ScheduleExpression: rate(7 days)
      - SourceAccountId: 111111111111
    targets:
      - path: 9999999999
        name: some-account
```

If the template that is being deployed contains a Transform, such as a Serverless Transform it needs to be packaged and uploaded to S3 in every region where it will need to be deployed. This can be achieved by setting the `contains_transform: true` parameter and updating the buildspec for your pipeline to call the `bash adf-build/helpers/package_transform.sh` script. This script will package your lambda to each region and generate a region specific template.yml for the pipeline deploy stages.

If you decide you no longer require a specific pipeline you can remove it from the deployment_map.yml file and commit those changes back to the *aws-deployment-framework-pipelines* repository *(on the deployment account)* in order for it to be cleaned up. The resources that were created as outputs from this pipeline will **not** be removed by this process.

#### Syntax

The Deployment map has a shorthand syntax along with a more detailed version when you need extra configuration for the *targets* key as detailed below:

**Shorthand:**

```yaml
targets:
  - 9999999999 # Single Account, Deployment Account region
  - /my_ou/production  # Group of Accounts, Deployment Account region
```

**Detailed:**

```yaml
targets:
  - path: 9999999999
    regions: eu-west-1
    name: my-special-account
  - path: /my_ou/production
    regions: eu-central-1
    name: production_step
```

## Deploying via Pipelines

### Repositories

Source entities for pipelines can consist of AWS CodeCommit Repositories, Amazon S3 Buckets or GitHub Repositories. Repositories are attached to pipelines in a 1:1 relationship, however, you can chose to clone or bring other repositories into your code during the build phase of your pipeline. You should define a suitable [buildspec](#buildspec) that matches your desired outcome and is applicable to the type of resource you are deploying.

### BuildSpec

If you are using [AWS CodeBuild](https://aws.amazon.com/codebuild/) as your build phase you will need to specify a [buildspec.yml](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html) file that will live along side your resources in your repository. This file defines how and what AWS CodeBuild will do during certain phases.

Lets take a look an example to breakdown how the AWS Deployment Framework uses `buildspec.yml` files to elevate heavy lifting when it comes to deploying CloudFormation templates.

*Note:* You can use [custom build](https://aws.amazon.com/blogs/devops/extending-aws-codebuild-with-custom-build-environments/) environments in AWS CodeBuild.

```yaml
version: 0.2

phases:
  install:
    commands:
      - aws s3 cp s3://$S3_BUCKET_NAME/adf-build/ adf-build/ --recursive --quiet # Copy down the shared modules from S3
      - pip install -r adf-build/requirements.txt -q # Install Requirements via requirements.txt
      - python adf-build/generate_params.py # Generate Parameter files dynamically
artifacts:
  files: '**/*' # Package up all outputs and pass them along to next stage
```

In the example we have fours steps to our install phase in our build, the remaining phases and steps you add are up to you. In the above steps we simply bring in the shared modules we will need to run our main function in *generate_params.py*. The $S3_BUCKET_NAME variable is available in AWS CodeBuild as we pass this in from our initial creation of the that defines the CodeBuild Project. You do not need to change this.

Other packages such as [cfn-lint](https://github.com/awslabs/cfn-python-lint) can be installed in order to validate that our CloudFormation templates are up to standard and do not contain any obvious errors. If you wish to add in any extra packages you can add them to the *requirements.txt* in the `bootstrap_repository` which is brought down into AWS CodeBuild and installed. Otherwise you can add them into any pipelines specific buildspec.yml.

### CloudFormation Parameters and Tagging

When you define CloudFormation templates as artifacts to push through a pipeline you might want to have a set of parameters associated with the templates. You can utilize the `params` folder in your repository to add in parameters as you see fit. To avoid having to create a parameter file for each of the stacks you wish to deploy to, you can create a parameter file called `global.json` any parameters defined in this file will be merged into the parameters for any specific account parameter file at run time. For example you might have a single parameter for a template called `CostCenter` the value of this will be the same across every deployment of your application however you might have another parameter called `InstanceType` that you want to be different per account. Using this example we can create a `global.json` file that contains the following JSON:

```json
{
    "Parameters": {
        "CostCenter": "department-abc"
    }
}
```

Then we can have a more specific parameter for another account, this file should be called `account.json` where account is the name of the account you wish to apply these parameters too.

```json
{
    "Parameters": {
        "InstanceType": "m5.large"
    }
}
```

When the stack is executed it will be executed with the following parameters:

```json
{
    "Parameters": {
        "InstanceType": "m5.large",
        "CostCenter": "department-abc"
    }
}
```

This aggregation of parameters works for a few different levels, where the most specific level takes precedence. In the example above, if CostCenter is defined in both `global.json` and `account.json` then the value in the `account.json` file will take precedence.

The different types of parameter files and their order of precedence *(in the tree below, the lowest level has the highest precedence)* can be used to simplify how parameters are specified. For example, a parameter such as `Environment` might be the same for all accounts under a certain OU, so placing it under a single `ou.json` params file means you don't need to populate it for each account under that OU.

**Note:** When using OU parameter files, the OU must be specified in the deployment map as a target. If only the account number is in the deployment map the corresponding OU parameter file will not be referenced.

```
global.json
|
|_ deployment_account_region.json (e.g. global_eu-west-1.json)
    |
    |_ ou.json (e.g. ou-1a2b-3c4d5e.json)
        |
        |_ ou_region.json (e.g. ou-1a2b-3c4d5e_eu-west-1.json)
            |
            |_ account.json (e.g. dev-account-1.json)
                |
                |_ account_region.json (e.g. dev-account-1_eu-west-1.json)
```

This concept also works for applying **Tags** to the resources within your stack. You can include tags like so:

```json
{
    "Parameters": {
        "CostCenter": "123",
        "Environment": "testing"
    },
    "Tags" : {
        "TagKey" : "TagValue",
        "MyKey" : "MyValue"
      }
}
```

This means that all resources that support tags within your CloudFormation stack will be tagged as defined above.

It is important to keep in mind that each Deployment Provider *(Code Deploy, CloudFormation, Service Catalog etc)* have their [own Parameter structure](https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-pipeline-structure.html) and configuration files. For example, Service catalog allows you to pass a configuration file as such:

```json
{
    "SchemaVersion": "1.1",
    "ProductVersionName": "test",
    "ProductVersionDescription": "My awesome product",
    "ProductType": "CLOUD_FORMATION_TEMPLATE",
    "Properties": {
        "TemplateFilePath": "/template.yml"
    }
}
```

You can create the above parameter files if you are deploying products to your Service Catalog's in the same fashion as with CloudFormation *(global.json etc)*.

For more examples of parameters and their usage see the `samples` folder in the root of the repository.

*Note:* Currently only Strings type values are supported as parameters to CloudFormation templates.

### Parameter Injection

Parameter injection solves problems that occur with Cross Account parameter access. This concept allows the resolution of values directly from SSM Parameter Store within the Deployment account into Parameter files *(eg global.json, account-name.json)* and also importing of exported values from CloudFormation stacks across accounts and regions.

If you wish to resolve values from Parameter Store on the Deployment Account directly into your parameter files you can do the the following:

```json
{
    "Parameters": {
        "Environment": "development",
        "InstanceType": "m5.large",
        "SomeValueFromSSM": "resolve:/my/path/to/value"
    }
}
```

When you use the special keyword **"resolve:"**, the value in the specified path will be fetched from Parameter Store on the deployment account during the CodeBuild Containers execution and populated into the parameter file for each account you have defined. If you plan on using any sensitive data, ensure you are using the [NoEcho](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) property to ensure it is kept out of the console and logs. Resolving parameters across regions is also possible using the notation of *resolve:region:/my/path/to/value*. This allows you to fetch values from the deployment account in other regions other than the main deployment region.

To highlight an example of how Parameter Injection can work well, think of the following scenario: You have some value that you wish to rotate on a monthly bases. You have some automation in place that updates the value of a Parameter store parameter to add in this new value. Each time this pipeline runs it will check for that value and update the resources accordingly, effectively detaching the parameters from the pipeline itself.

Parameter injection is also useful for importing exported values from CloudFormation stacks in other accounts or regions. Using the special **"import"** syntax you can access these values directly into your parameter files.

```json
{
    "Parameters": {
        "BucketInLoggingAccount": "import:123456789101:eu-west-1:stack_name:export_key"
    }
}
```

In the above example *123456789101* is the AWS Account Id in which we want to pull a value from, *eu-west-1* is the region, stack_name is the CloudFormation stack name and *export_key* is the output key name *(not export name)*.

### Nested Stacks

AWS CloudFormation allows stacks to create other stacks via the [nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html) feature. Since ADF supports a single entry template titled `template.yml` the stacks that you wish to nest will need to spawn from this template. Nested stacks allow users to pass a `TemplateURL` value that points directly to another CloudFormation template that is either in S3 or on the File System. If you reference a template on the file system you will need to use the `package_transform.sh` helper script during AWS CodeBuild execution *(during the build phase)* in your pipeline to package up the contents of your templates into finalized artifacts.

This can be achieved with a `buildspec.yml` like so:

```yaml
version: 0.2

phases:
  install:
    commands:
      - aws s3 cp s3://$S3_BUCKET_NAME/adf-build/ adf-build/ --recursive --quiet
      - pip install -r adf-build/requirements.txt -q
      - python adf-build/generate_params.py
  build:
    commands:
      - bash adf-build/helpers/package_transform.sh
artifacts:
  files: '**/*'
```

This allows us to specify nested stacks that are in the same repository as out main `template.yml` in our like so:

```yaml
  MyStack:
    Type: "AWS::CloudFormation::Stack"
    Properties:
      TemplateURL: another_template.yml # file path to the nested stack template
```

When the `package_transform.sh` command is executed, the file will be packaged up and uploaded to Amazon S3. Its *TemplateURL* key will be updated to point to the object in S3 and this will be a valid path when `template.yml` is executed in the deploy stages of your pipeline.

### Deploying Serverless Applications with SAM

Serverless Applications can also be deployed via ADF. The only extra step required to deploy a SAM template is that you execute `bash adf-build/helpers/package_transform.sh` from within your build stage like so:

For example, deploying a NodeJS Serverless Application from AWS CodeBuild with the *aws/codebuild/standard:2.0* image can be done with a *buildspec.yml* that looks like the following [read more](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html#runtime-versions-buildspec-file):

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.7
      nodejs: 10
  pre_build:
    commands:
      - aws s3 cp s3://$S3_BUCKET_NAME/adf-build/ adf-build/ --recursive --quiet
      - pip install -r adf-build/requirements.txt -q
      - python adf-build/generate_params.py
  build:
    commands:
      - bash adf-build/helpers/package_transform.sh
artifacts:
  files: '**/*'
```