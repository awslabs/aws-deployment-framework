## Sample IAM to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-iam*.

### Deployment Map example

```yaml
  - name: sample-iam
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111 # Some Source Account that contains the IAM CloudFormation template
      - RestartExecutionOnUpdate: True # Since this is a base type stack we would most likely want to retrigger this pipeline if a new account gets added to the below OU's
    targets: # Example Targets OU's
      - /banking/testing
      - /banking/production
```
