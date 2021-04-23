## Sample IAM to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-iam*.

### Deployment Map example

```yaml
  - name: sample-iam
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
      - /banking/production
```
