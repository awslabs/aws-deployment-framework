## Sample ECR Repository to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-ecr-repository
    type:
      source:
        name: codecommit
        account_id: 111111111111
    targets:
      - /deployment
```
