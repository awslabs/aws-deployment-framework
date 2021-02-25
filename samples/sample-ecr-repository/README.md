## Sample ECR Repository to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-ecr-repository
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
      - /deployment
```
