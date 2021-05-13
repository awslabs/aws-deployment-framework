## Sample Serverless Python based Application

### Deployment Map example

```yaml
  - name: sample-serverless-app
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
          environment_variables:
            CONTAINS_TRANSFORM: True
    targets:
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
