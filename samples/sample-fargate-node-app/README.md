# Sample NodeJS Web Application running on AWS Fargate

## Prerequisites

Please make sure you deploy the `sample-ecr-repository` and
`sample-ecs-cluster` examples before you deploy this sample.
The ECS cluster should be deployed to the same target accounts and region.

If you want to change the region to another region, please make sure to rename
the `params/global_eu-west-1.json` file to use the new region name.
For example: `params/global_us-east-1.json`.
Also update the regions list in the deployment map for this example.

## Deployment Map example

```yaml
  - name: sample-fargate-node-app
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_7_0"
          privileged: true
          # ^ Required for Docker in Docker to work as expected (since
          #   CodeBuild will run our docker commands to create and push our
          #   image).
    regions:
      - eu-west-1
    targets:
      # Example Targets: These accounts/regions have had the sample-vpc deployed
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
