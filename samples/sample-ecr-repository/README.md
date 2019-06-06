## Sample ECR Repository to showcase ADF Pipelines

### Deployment Map example

```yaml
  - name: sample-ecr-repository
    type: cc-cloudformation 
    params:
      - SourceAccountId: 111111111111
    targets:
      - /deployment # Some shared type account that would store shared Container Images
```