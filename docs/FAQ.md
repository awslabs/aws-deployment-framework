# FAQ

- Q: Why is the region us-east-1 required for the initial stack and why does it need to be in the master account of the Organization?
- > A: Organzations can only be accessed from the Master account of the Organization, read more about [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/APIReference/Welcome.html).

- Q: What are the limits of AWS CodePipeline?
- > A: Please read [AWS CodePipeline Limits](https://docs.aws.amazon.com/codepipeline/latest/userguide/limits.html).

- Q: I cannot get CodeCommit working nicely with git or it stops working after a short period of time.
- > A: Please read [Setting up CodeCommit](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up.html).

- Q: Can I make Pipelines that depend on other pipelines?
- > A: Each Pipeline you create can be passed a Parameter via the deployment_map.yml file called "RestartExecutionOnUpdate" which defaults to "false". If this is parameter is set to true then the pipeline will automatically execute when it is updated to include any new account, which is, each time an account is bootstrapped into a OU that the pipeline targets. This should be used for pipelines that are considered fundamental for all accounts as it will occur automatically. Using this parameter on every pipeline can cause pipelines that import and export values from each other to execute out of order and potentially fail.

- Q: How do I know what I can add in terms of pipeline_types? What are supported configuration options?
- > A: Read more about how AWS CodePipeline can [integrate](https://aws.amazon.com/codepipeline/product-integrations/) with other services, tools and even add [custom actions](https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-create-custom-action.html) to allow you to build the pipeline to suit your needs.

- Q: Can I make Pipelines target Organizational Units without any accounts in them?
- > A: No, in order for AWS CodePipeline to setup a pipeline that deploys into an account the roles that allow this action need to already exist on the target account.

- Q: What resources are in the `global.yml` file, can these be extended?
- > A: The `regional.yml` or `global.yml` can be extended to suit your needs when it comes to the bootstrapping process. However the `global.yml` that comes as a default is the minimal amount of required access needed to setup the Pipeline section of the AWS Deployment Framework. You can of course adjust some of the policies within the `adf-cloudformation-deployment-role` to better suit your requirements for certain OUs / Accounts. The `regional.yml` for the deployment account OU comes with the minimum required resources to allow for cross region AWS CodePipeline deployments and should not be removed.
