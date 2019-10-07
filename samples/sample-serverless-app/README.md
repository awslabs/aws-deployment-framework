## Sample Serverless Python based Application

### Deployment Map example

```yaml
  - name: sample-serverless-app
    type:
      source:
        name: codecommit
        account_id: 111111111111
      build:
        image: STANDARD_2_0
        environment_variables:
          CONTAINS_TRANSFORM: true
    targets:
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
