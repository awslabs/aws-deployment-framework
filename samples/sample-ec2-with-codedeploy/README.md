## Sample EC2 Application Stack with CodeDeploy Components

This example is coupled with the `sample-ec2-java-app-codedeploy` repository and is aimed at showcasing how to deploy a basic Springboot application with [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html) via ADF.

This stack assumes a Amazon EC2 [Key Pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html) has been created in the target accounts.

This stack is a generic stack for applications that run on Amazon EC2. This stack could be extended and used as a base for all line of business type applications that run Amazon EC2.

This stack also requires `sample-vpc` and `sample-iam` to be in deployed as it imports resources directly from both of them.

### Deployment Map example

#### This sample stack depends on resources in sample-iam and sample-vpc

```yaml
  - name: sample-ec2-app-codedeploy
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0" # So we can specify which Python version we need
    targets:
      - /banking/testing
      - /banking/production
```
