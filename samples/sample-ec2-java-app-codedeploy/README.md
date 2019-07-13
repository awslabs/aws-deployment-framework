## Sample SpringBoot application (Java) Running on EC2 deployed via CodePipeline

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-ec2-java-app-codedeploy*.

This example is coupled with the `sample-ec2-with-codedeploy` repository and is aimed at showcasing how to deploy a basic Springboot application with [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html) via ADF.

### Deployment Map example

```yaml
  - name: sample-ec2-java-app-codedeploy
    type: cc-codedeploy
    params:
      - SourceAccountId: 111111111111
      - Image: "aws/codebuild/standard:2.0"
    targets:
      - path: 222222222222
        regions: eu-west-1
        params: # params are used here to allow different values to be passed into different stages of your pipeline
          ApplicationName: sample
          DeploymentGroupName: testing-sample
      - path: 333333333333
        params:
          ApplicationName: sample
          DeploymentGroupName: production-sample
```
