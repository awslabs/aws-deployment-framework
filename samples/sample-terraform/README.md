## Sample Terraform 

### Deployment Map example

```yaml
  - name: my-terraform-example
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 1111111111111
      deploy:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
    targets:
      - properties:
          spec_filename: my_test_spec.yml
```
