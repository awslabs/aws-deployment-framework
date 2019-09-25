# Sample CDK Bootstrap pipeline

This pipeline is expecting *(in the example case)* an AWS CodeCommit repository
on the account `111111111111` in your main deployment region named
*sample-cdk-bootstrap*.

## Deployment Map example

```yaml
  - name: sample-cdk-bootstrap
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_7_0"
    targets:
      - /banking/testing
      - /banking/production
```
