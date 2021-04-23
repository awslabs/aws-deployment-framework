## Expunge VPC

This template uses a Custom Lambda backed resource to expunge the default VPC within all regions.

Upon stack deletion the default VPCs will be recreated.

### Deployment Map Example
```yaml
- name: expunge-vpc
  default_providers:
    source:
      provider: codecommit
      properties:
        account_id: 111111111111
    build:
      provider: codebuild
      properties:
        image: "STANDARD_4_0" # So we can specify which Python version we need
        environment_variables:
          CONTAINS_TRANSFORM: true # Required for templates that contain transforms. (eg SAM Templates)

  params:
    - restart_execution_on_update: true
  targets:
    - path: /test
      name: test-deployments
```
