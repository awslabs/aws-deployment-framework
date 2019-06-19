## Sample ECR Repository to showcase ADF Pipelines

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-ecr-repository*.

### Deployment Map example

```yaml
  - name: sample-ecr-repository
    type: cc-cloudformation
    params:
      - SourceAccountId: 111111111111
    targets:
      - /deployment # Some shared type account that would store shared Container Images
```
