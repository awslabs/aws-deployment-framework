# Terraform template

## Overview

Please read the [user guide on ADF's support for
Terraform](../../docs/user-guide.md#terraform-pipeline) before you proceed.

## Deployment procedure

1. Add a sample-terraform pipeline in ADF `deployment-map.yml` as in the
example:

```yaml
- name: sample-terraform
  default_providers:
    source:
      provider: codecommit
      properties:
        account_id: 111111111111  # Source account id
    build:
      provider: codebuild
    deploy:
      provider: codebuild
      properties:
        image: "STANDARD_5_0"
        environment_variables:
          TARGET_ACCOUNTS: 111111111111,222222222222  # Target accounts
          TARGET_OUS: /core/infrastructure,/sandbox  # Target OUs
          MANAGEMENT_ACCOUNT_ID: 333333333333  # Billing account
          # Regions in comma-separated list format, for example
          # "eu-west-1,us-east-1"
          REGIONS: eu-west-1
  targets:
    - name: terraform-scan  # optional
      properties:
        spec_filename: tf_scan.yml  # Terraform scan
    - name: terraform-plan
      properties:
        spec_filename: tf_plan.yml  # Terraform plan
    - approval  # manual approval
    - name: terraform-apply
      properties:
        spec_filename: tf_apply.yml  # Terraform apply
```

The sample uses the following configuration, please update accordingly:

- Project name: `sample-tf-module`
- Target accounts: `111111111111` and `222222222222`
- Target regions: `eu-west-1` (the main ADF deployment region) and `us-east-1`
