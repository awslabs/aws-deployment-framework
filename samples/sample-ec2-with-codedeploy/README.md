## Sample EC2 Application Stack with CodeDeploy Components

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-ec2-app-codedeploy*.

This example is coupled with the `sample-ec2-java-app-codedeploy` repository and is aimed at showcasing how to deploy a basic Springboot application with [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html) via ADF.

This stack assumes a Amazon EC2 [Key Pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html) has been created in the target accounts.

This stack is a generic stack for applications that run on Amazon EC2. This stack could be extended and used as a base for all line of business type applications that run Amazon EC2.

This stack also requires `sample-vpc` and `sample-iam` to be in deployed as it imports resources directly from both of them.

### Deployment Map example

#### This sample stack depends on resources in sample-iam and sample-vpc

```yaml
  - name: sample-ec2-app-codedeploy
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111
    targets:
      - 222222222222
      - 333333333333
```
