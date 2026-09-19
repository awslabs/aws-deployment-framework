# Sample IAM to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository
on the account `111111111111` in your main deployment region named *sample-iam*.

This sample is configured to deploy to the `eu-west-1` region.
If you would like to deploy it to another region, please update the
parameters in the `params/global.yml` file. Replacing the `eu-west-1` part
with the region you like to deploy to.

As all resources in this stack are globally accessible, this sample should only
be deployed to a single region per account. It is recommended to leave it
configured to the default deployment region of your ADF installation.

## Deployment Map example

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
          image: "STANDARD_7_0"
    params:
      restart_execution_on_update: True
    targets:
      - /banking/testing
      - /banking/production
```
