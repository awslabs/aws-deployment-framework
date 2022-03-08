# User Guide

- [Deployment Map](#deployment-map)
  - [Providers](#providers)
  - [Targets Syntax](#targets-syntax)
  - [Params](#params)
  - [Repositories](#repositories)
  - [Completion Triggers](#completion-triggers)
  - [Additional Triggers](#additional-triggers)
  - [Additional Deployment Maps](#additional-deployment-maps)
  - [Removing Pipelines](#removing-pipelines)
- [Deploying via Pipelines](#deploying-via-pipelines)
  - [BuildSpec](#buildspec)
  - [Parameters and Tagging](#cloudformation-parameters-and-tagging)
  - [Serverless Transforms](#serverless-transforms)
  - [Parameter Injection](#parameter-injection)
  - [Nested Stacks](#nested-cloudformation-stacks)
  - [Deploying Serverless Applications with SAM](#deploying-serverless-applications-with-sam)
  - [Using Anchors and Alias](#using-anchors-and-alias)
  - [One to many Relationships](#one-to-many-relationships)

## Deployment Map

The `deployment_map.yml` file *(or [files](#additional-deployment-maps))* lives in the repository named `aws-deployment-framework-pipelines` on the Deployment Account. These files are the general pipeline definitions that are responsible for mapping the specific pipelines to their deployment targets along with their respective parameters. The [AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html) will synthesize during the CodeBuild step within the `aws-deployment-framework-pipelines` pipeline. Prior to the CDK creating these pipeline templates, a input generation step will run to parse the deployment_map.yml files, it will then assume a readonly role on the master account in the Organization that will have access to resolve the accounts in the AWS Organizations OU's specified in the mapping file. It will return the account name and ID for each of the accounts and pass those values into the input files that will go on to be main CDK applications inputs.

The deployment map file defines the pipelines along with their inputs,
providers to use and their configuration. It also defines the targets of the
pipeline within a list type structure.

Each entry in the `'targets'` key list represents a stage within the pipeline
that will be created. The deployment map files also allow for some unique steps
and actions to occur in your pipeline. For example, you can add an approval
step to your pipeline by putting a step in your targets definition titled,
`'approval'`. This will add a manual approval stage at this point in your
pipeline.

A basic example of a `deployment_map.yml` would look like the following:

```yaml
pipelines:
  - name: iam
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111  # The AWS Account where the source code will be in a CodeCommit Repository
    params:
      notification_endpoint: janes_team@example.com  # Optional
    tags:
      foo: bar # Pipelines support tagging
    targets:
      - path: /security
        regions: eu-west-1
      - approval  # This is a shorthand example of an approval step within a pipeline
      - /banking/testing  # This is a shorthand example of a step within a pipeline targeting an OU

  - name: vpc
    default_providers:
      source:
        provider: github
        properties:
          repository: my-github-vpc # Optional, above name property will be used if this is not specified
          owner: bundyfx # Who owns this Github Repository
          oauth_token_path: /adf/github_token # The path in AWS Secrets Manager that holds the GitHub Oauth token, ADF only has access to /adf/ prefix in Secrets Manager
          json_field: token # The field (key) name of the json object stored in AWS Secrets Manager that holds the Oauth token
    params:
      notification_endpoint: joes_team@example.com
    targets:
      - path: /banking/testing
        name: fancy-name #Optional way to pass a name for this stage in the pipeline
```

In the above example we are creating two pipelines with AWS CodePipeline. The first one will deploy from a repository named **iam** that lives in the account `111111111111`. This CodeCommit Repository will automatically be created by default in the `111111111111` AWS Account if it does not exist. The automatic repository creation occurs if you enable `'auto-create-repositories'` (which is enabled by default). The `iam` pipeline will use AWS CodeCommit as its source and deploy in 3 steps. The first stage of the deployment will occur against all AWS Accounts that are in the `/security` Organization unit and be targeted to the `eu-west-1` region. After that, there is a manual approval phase which is denoted by the keyword `approval`. The next step will be targeted to the accounts within the `/banking/testing` OU *(in your default deployment account region)* region. By providing a simple path without a region definition it will default to the region chosen as the deployment account region in your [adfconfig](./admin-guide/adfconfig.yml). Any failure during the pipeline will cause it to halt.

The second pipeline (*vpc*) example deploys to an OU path `/banking/testing`. You can choose between an absolute path in your AWS Organization, AWS Account ID or an array of OUs or IDs. This pipeline also uses Github as a source rather than AWS CodeCommit. When generating the pipeline, ADF expects [GitHub Token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line) to be placed in AWS Secrets Manager in a path prefixed with `/adf/`.

By default, the above pipelines will be created to deploy CloudFormation using a change in two actions *(Create then Execute)*.

#### Targeting via Tags

Tags on AWS Accounts can also be used to define stages within a pipeline. For example, we might want to create a pipeline that targets all AWS Accounts with the tag `cost-center` and value of `foo-team`. You cannot use a combination of `path/target` and `tags`.

We do that with the following syntax:

```yaml
pipelines:
  - name: vpc-for-foo-team
    default_providers:
      # ...
    targets:
      - tags: # Using tags to define the stage rather than a path or account id
          cost-center: foo-team
        name: foo-team # You can optionally use the name key to give this stage some meaningful name
```

Adding or Removing Tags to an AWS Account in AWS Organizations will automatically trigger a run of the bootstrap pipeline which will in turn execute the pipeline generation pipeline in the deployment account.

### Important Notes

#### Zero-prefixed AWS Account Ids

In most cases, you can target accounts directly by passing the AWS Account Id
as an integer, as shown in the example above. However, in case the AWS Account
Id starts with a zero, for example `012345678910`, you will need to pass the
AWS Account Id as a string instead.

Due to the way the YAML file is read, it will automatically transform
zero-leading numbers by removing the zero. Additionally, if the AWS Account Id
starts with a zero and happens to include numbers between 0 and 7 only, for
example `012345671234`, it will treat it as a octal number instead.
Since this cannot be detected without making risky assumptions, the deployment
will error to be on the safe side instead.

### Providers

The ADF comes with an extensive set of abstractions over CodePipeline providers
that can be used to define pipelines. For example, see the following pipeline
definition:

```yaml
pipelines:
  - name: sample-ec2-java-app-codedeploy
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        image: "STANDARD_5_0" # Use a specific docker image (supports Python 3.7, 3.8, and 3.9) for the build stage in this pipeline -> https://docs.aws.amazon.com/cdk/api/latest/docs/@aws-cdk_aws-codebuild.LinuxBuildImage.html
      deploy:
        provider: codedeploy
    targets:
      - target: 999999999999
        properties:
          application_name: sample
          deployment_group_name: testing-sample # https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups.html
```

The pipeline `sample-ec2-java-app-codedeploy` has a `default_providers` key
that defines the high-level structure of the pipeline.
It explicitly defines the source *(requirement for all pipelines)* and also
defines what type of build will occur along with any associated parameters.

In this example, we're explicitly saying we want to use AWS CodeBuild
*(which is also the default)* and also to use a specific Docker Image for build
stage. The default deployment provider for this pipeline is configured to be
`codedeploy` in this example. This means that any of the targets of the
pipeline will use AWS CodeDeploy as their default
[Deployment Provider](https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-pipeline-structure.html#actions-valid-providers).

In the targets section itself we have the opportunity to override the provider
itself or pass in any additional properties to that provider. In this example
we are passing in `application_name` and *deployment_group_name* as properties
to CodeDeploy for this specific stage. The `properties` can either be defined
by changing the `default_providers` configuration or get updated at the stage
level. Stage level config overrides default provider config.

By default, the build provider is AWS CodeBuild and the deployment provider is
AWS CloudFormation.

For detailed information on providers and their supported properties, see the
[providers guide](./providers-guide.md).

### Targets Syntax

The Deployment Map has a shorthand syntax along with a more detailed version when you need extra configuration for the *targets* key as detailed below:

**Shorthand:**

```yaml
targets:
  - 9999999999 # Single Account, Deployment Account Region
  - /my_ou/production  # Group of Accounts, Deployment Account Region
```

**Detailed:**

```yaml
targets:
  - target: 9999999999 # Target and Path keys can be used interchangeably
    regions: eu-west-1
    name: my-special-account # Defaults to adf-cloudformation-deployment-role
    provider: some_provider # If you intend to override the provider for this stage (see providers guide for available providers)
    properties:
      my_prop: my_value # If you intend to pass properties to this specific stage
  - path: /my_ou/production # This can also be an array of OUs or AWS Account IDs
    regions: [eu-central-1, us-west-1]
    name: production_step
    provider: ...
    properties: ...
  - path: /my_ou/production/some_path
    regions: [eu-central-1, us-west-1]
    name: another_step
    wave:
      size: 30 # (Optional) This forces the pipeline to split this OU into seperate stages, each stage containing up to X accounts
    exclude: 
      - 9999999999 # (Optional) List of accounts to exclude from this target. Currently only supports account Ids 
    properties: ...    
```

CodePipeline has a limit of 50 actions per stage.
A stage is identified in the above list of targets with a new entry in the array, using `-`.

To workaround this limit, ADF will split the accounts x regions that are selected as part of one stage over multiple stages when required.
A new stage is introduced for every 50 accounts/region deployments by default. The default of 50 will make sense for most pipelines.
However, in some situations, you would like to limit the rate at which an update is rolled out to the list of accounts/regions.
This can be configured using the `wave/size` target property. Setting these to `30` as shown above, will introduce a new stage for every 30 accounts/regions.
If the `/my_ou/production/some_path` OU would contain 25 accounts (actually 26, but account `9999999999` is excluded by the setup above), multiplied by the two regions it targets in the last step, the total of account/region deployment actions required would be 50.
Since the configuration is set to 30, the first 30 accounts will be deployed to in the first stage. If all of these successfully deploy, the pipeline will continue to the next stage, deploying to the remaining 20 account/regions.

### Params

Pipelines also have parameters that don't relate to a specific stage but rather the pipeline as a whole. For example, a pipeline might have an single notification endpoint in which it would send a notification when it completes or fails. It also might have things such as a schedule for how often it runs.

The following are the available pipeline parameters:

- *notification_endpoint* *(String) | (Dict) * defaults to none.
  > Can either be a valid email address or a string that represents the name of a Slack Channel. 
  > A more complex configuration can be provided to integrate with Slack via AWS ChatBot. 
  > ```yaml
  > notification_endpoint:
  >   type: chat_bot
  >   target: example_slack_channel  # This is the name of an slack channel configuration you created within the AWS Chat Bot service. This needs to be created before you apply the changes to the deployment map.
  > ```
  >
  > In order to integrate ADF with Slack see [Integrating with Slack](./admin-guide.md#integrating-with-slack-with-aws-chatbot) in the admin guide. By default, notifications will be sent when pipelines Start, Complete, or Fail.

- *schedule* *(String)* defaults to none.
  > If the Pipeline should execute on a specific Schedule. Schedules are defined by using a Rate or an Expression. See [here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions) for more information on how to define Rate or an Expression.

- *restart_execution_on_update* *(Boolean)* default: `False`.
  > If the Pipeline should start a new execution if its structure is updated. Pipelines can often update their structure if targets of the pipeline are Organizational Unit paths. This setting allows pipelines to automatically run once an AWS Account has been moved in or out of a targeted OU.

### Completion Triggers

Pipelines can also trigger other pipelines upon completion. To do this, use the *on_complete* key on the triggers definition. For example:

```yaml
pipelines:
  - name: ami-builder
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 222222222222
      build:
        provider: codebuild
        role: packer
        size: medium
    params:
      schedule: rate(7 days)
    triggers: # What should trigger this pipeline, and what should be triggered when it completes
      on_complete:
        pipelines:
          - my-web-app-pipeline # Start this pipeline

  - name: my-web-app-pipeline
    default_providers:
      source:
        provider: github
        properties:
          repository: my-web-app
          owner: cool_coder
          oauth_token_path: /adf/github_token
          json_field: token
    targets:
      - path: /banking/testing
        name: web-app-testing
```

Completion triggers can also be defined in a short handed fashion. Take the above example for the ami-builder pipeline.
```yaml
pipelines:
  - name: ami-builder
    # Default providers and parameters are the same as defined above.
    # Only difference: instead of using `triggers` it uses the `completion_triggers`
    params:
      schedule: rate(7 days)
    completion_triggers: # What should trigger this pipeline, and what should be triggered when it completes
      pipelines:
        - my-web-app-pipeline # Start this pipeline

  - name: my-web-app-pipeline
    # Same configuration as defined above.
```


### Additional Triggers

Pipelines can also be triggered by other events using the *triggered_by* key on the triggers definition. For example, a new version of a package hosted on CodeArtifact being published:

```yaml
pipelines:
  - name: ami-builder
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 222222222222
      build:
        provider: codebuild
        role: packer
        size: medium
    triggers: # What should trigger this pipeline, and what should be triggered when it completes
      triggered_by:
        code_artifact:
          repository: my_test_repository
```

In the above example, the *ami-builder* pipeline is triggered when a new package version is published to the *my_test_repository* repository in CodeArtifact. 

### Additional Deployment Maps

You can also create additional deployment map files.
These can live in a folder in the pipelines repository called *deployment_maps*.
These are entirely optional, but can help split up complex environments with many pipelines.

For example, you might have a map used for infrastructure type pipelines and one used for deploying applications.
These additional deployment map files can have any name, as long as they end with *.yml*.

Taking it a step further, you can create a map per service.
So you can organize these deployment map files inside your preferred directory structure
For example, the `aws-deployment-framework-pipelines` repo could look like this:

```
deployment_maps/
  security/
    amazon-guardduty.yml
    aws-config.yml
  product-one/
    roles/
      some-role-pipeline.yml
    infrastructure/
      some-infra-pipeline.yml
```

### Repositories

Source entities for pipelines can consist of AWS CodeCommit Repositories, Amazon S3 Buckets or GitHub Repositories. Repositories are attached to pipelines in a 1:1 relationship, however, you can choose to clone or bring other repositories into your code during the build phase of your pipeline. You should define a suitable [buildspec](#buildspec) that matches your desired outcome and is applicable to the type of resource you are deploying.

### Removing Pipelines

If you decide you no longer require a specific pipeline you can remove it from the deployment_map.yml file and commit those changes back to the *aws-deployment-framework-pipelines* repository *(on the deployment account)* in order for it to be cleaned up. The resources that were created as outputs from this pipeline will **not** be removed by this process.

## Deploying via Pipelines

### BuildSpec

If you are using [AWS CodeBuild](https://aws.amazon.com/codebuild/) as your build phase you will need to specify a [buildspec.yml](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html) file that will live along side your resources in your repository. This file defines how and what AWS CodeBuild will do during certain phases.

Let's take a look an example to breakdown how the AWS Deployment Framework uses `buildspec.yml` files to elevate heavy lifting when it comes to deploying CloudFormation templates.

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

In the example we have three steps to our install phase in our build, the remaining phases and steps you add are up to you. In the above steps we simply bring in the shared modules we will need to run our main function in *generate_params.py*. The $S3_BUCKET_NAME variable is available in AWS CodeBuild as we pass this in from our initial creation of the that defines the CodeBuild Project. You do not need to change this.

Other packages such as [cfn-lint](https://github.com/awslabs/cfn-python-lint) can be installed in order to validate that our CloudFormation templates are up to standard and do not contain any obvious errors. If you wish to add in any extra packages you can add them to the *requirements.txt* in the `bootstrap_repository` which is brought down into AWS CodeBuild and installed. Otherwise you can add them into any pipelines specific buildspec.yml.

If you wish to hide away the steps that can occur in AWS CodeBuild, you can move the *buildspec.yml* content itself into the pipeline by using the *spec_inline* property in your map files. By doing this, you can remove the option to have a buildspec.yml in the source repository at all. This is a potential way to enforce certain build steps for certain pipeline types.

#### Custom Build Images
You can use [custom build](https://aws.amazon.com/blogs/devops/extending-aws-codebuild-with-custom-build-environments/) environments in AWS CodeBuild. This can be defined in the your deployment map files like so:

```yaml
pipelines:
  - name: example-custom-image
    default_providers:
      source:
        # ...
      build:
        provider: codebuild
        image:
          repository_arn: arn:aws:ecr:region:111111111111:repository/test
          tag: latest # optional (defaults to latest)
    targets:
      - # ...
```

Public images from docker hub can be defined in your deployment map like so:

```yaml
pipelines:
  - name: example-custom-image
    default_providers:
      source:
        # ...
      build:
        provider: codebuild
        properties:
          image: docker-hub://bitnami/mongodb
    targets:
      - # ...
```

### CloudFormation Parameters and Tagging

When you define CloudFormation templates as artifacts to push through a pipeline you might want to have a set of parameters associated with the templates. You can utilize the `params` folder in your repository to add in parameters as you see fit. To avoid having to create a parameter file for each of the stacks you wish to deploy to, you can create a parameter file called `global.yml` *(or .json)* any parameters defined in this file will be merged into the parameters for any specific account parameter file at build time. For example you might have a single parameter for a template called `CostCenter` the value of this will be the same across every deployment of your application however you might have another parameter called `InstanceType` that you want to be different per account. Using this example we can create a `global.yml` file that contains the following content:

```yaml
Parameters:
    CostCenter: department-abc
```

This can be represented in *json* in the same way if desired.

```json
{
    "Parameters": {
        "CostCenter": "department-abc"
    }
}
```

Then we can have a more specific parameter for another account, this file should be called `account.yml` where account is the name of the account you wish to apply these parameters too.

```yaml
Parameters:
    InstanceType: m5.large
```

When the stack is executed it will be executed with the following parameters:

```yaml
Parameters:
    InstanceType: m5.large
    CostCenter: department-abc
```

This aggregation of parameters works for a few different levels, where the most specific level takes precedence. In the example above, if *CostCenter* is defined in both `global.yml` and `account.yml` *("account" here represents the name of the account)* then the value in the `account.yml` file will take precedence.

The different types of parameter files and their order of precedence *(in the tree below, the lowest level has the highest precedence)* can be used to simplify how parameters are specified. For example, a parameter such as `Environment` might be the same for all accounts under a certain OU, so placing it under a single `ou.yml` params file means you don't need to populate it for each account under that OU.

**Note:** When using OU parameter files, the OU must be specified in the deployment map as a target. If only the account number is in the deployment map the corresponding OU parameter file will not be referenced.

```
global.yml
|
|_ deployment_account_region.yml (e.g. global_eu-west-1.yml)
    |
    |_ ou.yml (e.g. ou-1a2b-3c4d5e.yml)
        |
        |_ ou_region.yml (e.g. ou-1a2b-3c4d5e_eu-west-1.yml)
            |
            |_ account.yml (e.g. dev-account-1.yml)
                |
                |_ account_region.yml (e.g. dev-account-1_eu-west-1.yml)
```

This concept also works for applying **Tags** to the resources within your stack. You can include tags like so:

```yml
Parameters:
    CostCenter: '123'
    Environment: testing
Tags:
    TagKey: TagValue
    MyKey: MyValue
```

Again this example in *json* would look like:

```json
{
    "Parameters": {
        "CostCenter": "123",
        "Environment": "testing"
    },
    "Tags": {
        "TagKey": "TagValue",
        "MyKey": "MyValue"
    }
}
```

This means that all resources that support tags within your CloudFormation stack will be tagged as defined above.

It is important to keep in mind that each Deployment Provider *(Code Deploy, CloudFormation, Service Catalog etc)* have their [own parameter structure](https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-pipeline-structure.html) and configuration files. For example, Service catalog allows you to pass a configuration file as such:

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

You can create the above parameter files if you are deploying products to your Service Catalog's in the same fashion as with CloudFormation *(global.yml etc)*.

For more examples of parameters and their usage see the `samples` folder in the root of the repository.

*Note:* Currently only Strings type values are supported as parameters to CloudFormation templates when deploying via AWS CodePipeline.

### Serverless Transforms

If the template that is being deployed contains a transform, such as a Serverless Transform it needs to be packaged and uploaded to S3 in every region where it will be deployed. This can be achieved by setting the `CONTAINS_TRANSFORM` environment variable to *True* in your pipeline definition with a deployment map file. Once the environment variable has been set, within your *buildspec.yml* file you will need to use the *package_transform.sh* helper script (`bash adf-build/helpers/package_transform.sh`). This script will package your template to each region and transparently generate a region specific template for the pipeline deploy stages.

```yaml
pipelines:
  - name: example-contains-transform
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 222222222222
      build:
        provider: codebuild
        properties:
          environment_variables:
            CONTAINS_TRANSFORM: True # If you define this environment variable its expected that you are using the contains_transform helper in your build stage.
    targets:
      - /banking/testing
```

### Parameter Injection

Parameter injection solves problems that occur with Cross Account parameter access. This concept allows the resolution of values directly from SSM Parameter Store within the Deployment account into Parameter files *(eg global.json, account-name.json)* and also importing of output values from CloudFormation stacks across accounts and regions.

#### Retrieving parameter values

If you wish to resolve values from Parameter Store on the Deployment Account directly into your parameter files you can do the the following:

```yaml
Parameters:
    Environment: development
    InstanceType: m5.large
    SomeValueFromSSM: resolve:/my/path/to/value
```

When you use the special keyword **"resolve:"**, the value in the specified path will be fetched from Parameter Store on the deployment account during the CodeBuild Containers execution and populated into the parameter file for each account you have defined. If you plan on using any sensitive data, ensure you are using the [NoEcho](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) property to ensure it is kept out of the console and logs. Resolving parameters across regions is also possible using the notation of *resolve:region:/my/path/to/value*. This allows you to fetch values from the deployment account in other regions other than the main deployment region.

To highlight an example of how Parameter Injection can work well, think of the following scenario: You have some value that you wish to rotate on a monthly basis. You have some automation in place that updates the value of a Parameter store parameter on a schedule. Each time this pipeline runs it will check for that value and update the resources accordingly, effectively detaching the parameters from the pipeline itself.

There is also the concept of optionally resolving or importing values. This can be achieved by ending the import or resolve function with a **?**. For example, if you want to resolve a value from Parameter Store that might or might not yet exist you can use an optional resolve *(eg resolve:/my/path/to/myMagicKey?)*. If the key *myMagicKey* does not exist in Parameter Store then an empty string will be returned as the value.

#### Importing output values

Parameter injection is also useful for importing output values from CloudFormation stacks in other accounts or regions. Using the special **"import"** syntax you can access these values directly into your parameter files.

```yaml
Parameters:
    BucketInLoggingAccount: 'import:111111111111:eu-west-1:stack_name:output_key'
```

In the above example *111111111111* is the AWS Account Id in which we want to pull a value from, *eu-west-1* is the region, stack_name is the CloudFormation stack name and *output_key* is the output key name *(not export name)*. Again, this concept works with the optional style syntax *(eg, import:111111111111:eu-west-1:stack_name:output_key?)* if the key *output_key* does not exist at the point in time when this specific import is executed, it will return an empty string as the parameter value rather than an error since it is considered optional.

#### Uploading assets

Another built-in function is **upload**, You can use *upload* to perform an automated upload of a resource such as a template or file into Amazon S3 as part of the build process.
Once the upload is complete, the Amazon S3 URL for the object will be put in place of the *upload* string in the parameter file.

For example, If you are deploying products that will be made available via Service Catalog to many teams throughout your organization *(see samples)* you will need to reference the AWS CloudFormation template URL of the product as part of the template that creates the product definition. The problem that the **upload** function is solving in this case is that the template URL of the product cannot exist at this point, since the file has not yet been uploaded to S3.

```yaml
Parameters:
    ProductYTemplateURL: 'upload:path:productY/template.yml'
```

In the above example, we are calling the **upload** function on a file called `template.yml` that lives in the *productY* folder within our repository and then returning the path style URL from S3 (indicated by the word *path* in the string). The string *"upload:path:productY/template.yml"* will be replaced by the URL of the object in S3 once it has been uploaded.

Syntax:

```
# Using the default region:
upload:${style}:${local_path}

# Or, when you would like to choose a specific region:
upload:${region}:${style}:${local_path}
```

There are five different styles that one could choose from.

* `path` style, as shown in the example above, will return the S3 path to the object as.
  This is referred to as the classic [Path Style method](https://docs.aws.amazon.com/AmazonS3/latest/dev/VirtualHosting.html).
  * In case the bucket is stored in us-east-1, it will return:
    `https://s3.amazonaws.com/${bucket}/${key}`
  * In case the bucket is stored in any other region, it will return:
    `https://s3-${region}.amazonaws.com/${bucket}/${key}`
* `virtual-hosted` style, will return the S3 location using the virtual hosted bucket domain.
  * In case the bucket is stored in us-east-1, it will return:
    `https://${bucket}.s3.amazonaws.com/${key}`
  * In case the bucket is stored in any other region, it will return:
    `https://${bucket}.s3-${region}.amazonaws.com/${key}`
* `s3-url` style, will return the S3 location using S3 URL with the `s3://` protocol.
  As an example, this style is required for [CloudFormation AWS::Include transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html). 
  * It returns: `s3://${bucket}/${key}`
* `s3-uri` style, will return the S3 location using S3 URI without specifying a protocol.
  As an example, this style is required for [CodeBuild project source locations](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-codebuild-project-source.html#cfn-codebuild-project-source-location).
  * It returns: `${bucket}/${key}`
* `s3-key-only` style, similar to `s3-uri` but it will only return the `key` value.
  * It returns: `${key}`

The `region` is optional.
This allows you to upload files to S3 Buckets within specific regions by
adding in the region name as part of the string
(eg. `upload:us-west-1:path:productY/template.yml`).

The `local_path` references the files that you would like to be uploaded from
the location where `adf-build/generate-params.py` scripts gets executed from.
As shown in the example shared above, the file to upload would be the
`productY/template.yml` file that is stored in the root of the repository.

The bucket being used to hold the uploaded object is the same Amazon S3 Bucket that holds deployment artifacts *(On the Deployment Account)* for the specific region which they are intended to be deployed to. Files that are uploaded using this functionality will receive a random name each time they are uploaded.

### Nested CloudFormation Stacks

AWS CloudFormation allows stacks to create other stacks via the [nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html) feature. ADF supports a single entry template which defaults to `template.yml`, the stacks that you wish to nest will need to spawn from this template. Nested stacks allow users to pass a `TemplateURL` value that points directly to another CloudFormation template that is either in S3 or on the File System. If you reference a template on the file system you will need to use the `package_transform.sh` helper script during AWS CodeBuild execution *(during the build phase)* in your pipeline to package up the contents of your templates into finalized artifacts.

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

This allows us to specify nested stacks that are in the same repository as our main `template.yml` in our like so:

```yaml
  MyStack:
    Type: "AWS::CloudFormation::Stack"
    Properties:
      TemplateURL: another_template.yml # file path to the nested stack template
```

When the `package_transform.sh` command is executed, the file will be packaged up and uploaded to Amazon S3. Its *TemplateURL* key will be updated to point to the object in S3 and this will be a valid path when `template.yml` is executed in the deploy stages of your pipeline.

### Deploying Serverless Applications with SAM

Serverless Applications can also be deployed via ADF *(see samples)*. The only extra step required to deploy a SAM template is that you execute `bash adf-build/helpers/package_transform.sh` from within your build stage like so:

For example, deploying a NodeJS Serverless Application from AWS CodeBuild with the *aws/codebuild/standard:2.0* image can be done with a *buildspec.yml* that looks like the following [read more](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html#runtime-versions-buildspec-file):

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.9
      nodejs: 12
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

### Using Anchors and Alias

You can take advantage of YAML Anchors and Alias' in the deployment map files. As you can see from the example below, The &generic_params and &generic_targets are anchors. They can be added to any mapping, sequence or scalar. Once you create an anchor, you can reference it anywhere within the map again with its alias *(eg *generic_params)* to reproduce their values, similar to variables.

```yaml
pipelines:
  - name: sample-vpc
    default_providers:
      source: &generic_provider
        provider: codecommit
        properties:
          account_id: 111111111111
    targets: &generic_targets
      - /banking/testing
      - approval
      - path: /banking/production
        regions: eu-west-1

  - name: some-other-pipeline
    default_providers:
      source: *generic_provider
    targets: *generic_targets
```

If you want to define anchors before you use them as an alias, you can use any top-level key that starts with `x-` or `x_`. For example, if you want to define all account ids in one place, you could write:

```yaml
x_account_ids:
  - &codecommit_account: "111111111111"
  - &some_target_account: "222222222222"
pipelines:
  - name: sample-vpc
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: *codecommit_account
    targets:
      - *some_target_account
```

For more advanced yaml usage, see [here](https://learnxinyminutes.com/docs/yaml/)

### One to many relationships

If required, it is possible to create multiple Pipelines that are tied to the same Repository.

```yaml
pipelines:
  - name: sample-vpc-eu-west-1
    default_providers: &generic_source
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
          repository: sample-vpc
    regions: eu-west-1
    targets: &generic_targets
      - /banking/testing
      - approval
      - /banking/production

  - name: sample-vpc-us-east-1
    default_providers: *generic_source
    regions: us-east-1
    targets: *generic_targets
```

By passing in the Repository name *(repository)* we are overriding the **name** property which normally is the name of our associated repository. This will tie both of these pipelines to the single *sample-vpc* repository on the *111111111111* AWS Account.
