## Sample VPC to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-vpc*.

### Deployment Map example

```yaml
  - name: sample-vpc
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111 # Some Source Account that contains this Repository
      - RestartExecutionOnUpdate: True # Since this is a base type stack we would most likely want to retrigger this pipeline if a new account gets added to the below OU's
    targets:
      - /banking/testing
      - path: /banking/production
        regions: eu-west-1
        name: production
```
