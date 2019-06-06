## Sample NodeJS Web Application running on AWS Fargate

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
