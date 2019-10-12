## Sample ECS Cluster to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-ecs-cluster
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
    targets:
      - 222222222222
      - path: 333333333333
        regions: eu-west-1
        name: production
```
