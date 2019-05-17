## Sample VPC to showcase ADF Pipelines

### Deployment Map example
```yaml
  - name: sample-node-app
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111 # Some Source Account that contains this Repository
    targets: # Example Targets OU's
      - /banking/testing
      - path: /banking/production
        regions: eu-west-1
        name: production
```
