## Sample CDK Application to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-cdk-application*.

### Deployment Map example

```yaml
  - name: sample-cdk-application
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111
      - Image: "aws/codebuild/standard:2.0"
    targets:
      - /banking/testing
      - /banking/production
```
