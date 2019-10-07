## Sample SpringBoot application (Java) Running on EC2 deployed via CodePipeline

This example is coupled with the `sample-ec2-with-codedeploy` repository and is aimed at showcasing how to deploy a basic Java Springboot application with [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html) via ADF.

### Deployment Map example

```yaml
  - name: sample-ec2-java-app-codedeploy # A CodeCommit repo would be created automatically on the source account if it did not exist with this name, granted you are using CodeCommit as a source below.
    type:
      source:
        name: codecommit
        account_id: 11111111111 # Some AWS Account where the source code for this Java app would live
      build:
        name: codebuild
        image: "STANDARD_2_0" # Since we're building a Java application here we want to use STANDARD_2_0 (Ubuntu) as our base CodeBuild Image, that way we can tell it to have Java ready for us so we can build, compile and test our application.
      deploy:
        name: codedeploy # We will deploy out application with AWS CodeDeploy.
    targets:
      - path: 9999999999 # In this example we only want to deploy to a single AWS Account, so we include its account ID here.
        type:
          deploy: # These are Parameters for this specific stage in the pipeline, CodeDeploy needs to know which application and deployment group it should use to deploy. These resources would typically be deployed in a different stack as they are more part of the infrastructure to support the application as opposed to the application itself.
            application_name: sample
            deployment_group_name: testing-sample # https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups.html
```
