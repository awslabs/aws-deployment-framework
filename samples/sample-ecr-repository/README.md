## Sample ECR Repository to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-ecr-repository
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
    targets:
      - /deployment
```
