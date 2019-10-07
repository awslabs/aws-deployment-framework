## Sample VPC to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-vpc
    type:
      source:
        name: codecommit
        account_id: 111111111111
    params:
      restart_execution_on_update: True
    targets:
      - /banking/testing
      - path: /banking/production
        regions: eu-west-1
        name: production
```
