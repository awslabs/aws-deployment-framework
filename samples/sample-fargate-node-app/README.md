## Sample NodeJS Web Application running on AWS Fargate


### Deployment Map example
```yaml
  - name: sample-node-app
    type:
      source:
        name: codecommit
        account_id: 111111111111
      build:
        name: codebuild
        image: "STANDARD_2_0"
        privileged: true # Required for Docker in Docker to work as expected (Since CodeBuild will run our docker commands to create and push our image)
    targets: # Example Targets - These accounts/regions have had the sample-vpc deployed
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
