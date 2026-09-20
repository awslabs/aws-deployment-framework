# Sample ECS Cluster to showcase ADF Pipelines

## Prerequisites

Please make sure you deploy the `sample-vpc` example before you deploy
this sample. The VPC should be deployed to the same target accounts and region.

## Deployment Map example

```yaml
  - name: sample-ecs-cluster
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_7_0" # So we can specify which Python version we need
    targets:
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
