## Sample Serverless Python based Application

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-serverless-app*.

### Deployment Map example

```yaml
  - name: sample-serverless-app
    type: cc-cloudformation
    contains_transform: true # Required for templates that contain transforms. (eg SAM Templates)
    params:
      - SourceAccountId: 111111111111 # Some Source Account that contains this Repository
      - Image: "aws/codebuild/standard:2.0"
    targets:
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
