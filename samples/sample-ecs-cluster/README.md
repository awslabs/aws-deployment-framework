## Sample ECS Cluster to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-ecs-cluster*.

### Deployment Map example

```yaml
  - name: sample-ecs-cluster
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111
    targets: # Same targets as the sample-vpc since this cluster depends on outputs from the VPC Stack
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```