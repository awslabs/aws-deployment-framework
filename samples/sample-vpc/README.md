## Sample VPC to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-vpc
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
    params:
      restart_execution_on_update: True
    targets:
      - /banking/testing
      - path: /banking/production
        regions: eu-west-1
        name: production
```
