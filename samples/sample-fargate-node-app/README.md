## Sample NodeJS Web Application running on AWS Fargate

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-node-app*.

### Deployment Map example
```yaml
  - name: sample-node-app
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111 # Some Source Account that contains this Repository
      - Image: "aws/codebuild/standard:2.0"
    targets: # Example Targets - These accounts have had the sample-vpc deployed
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
