## Sample CDK Application to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-cdk-application*.

### Deployment Map example

```yaml
  - name: sample-cdk-application
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_2_0"
    targets:
      - /banking/testing
      - /banking/production
```
