# Terraform template

## Overview

This repository contains a module that manage the deployment of terraform code to multiple accounts and regions.
The module consists of three build stages defined in the following file:

- `buildspec.yml`: install the version of terraform specified in the pipeline configuration
- `tf_scan.yml`: (optional) returns any vulnerabilities in terraform code according with terrascan utilitiy
- `tf_plan.yml`: get the list of accounts from the organization and run a terraform plan
- `tf_apply.yml`: run a terraform apply after the manual step approval

## Parameters

- TERRAFORM_VERSION: the terraform version used to deploy the resource
- TARGET_ACCOUNTS: comma separated list of target accounts
- TARGET_OUS: comma separated list of target leaf OUs (parent OUs are supported)
- REGIONS: comma separated list of target region

### Deployment procedure

1. Add a sample-terraform pipeline in ADF `deployment-map.yml` as in the example:

```yaml
- name: sample-terraform
  default_providers:
    source:
      provider: codecommit
      properties:
        account_id: 111111111111 # source account id
    build:
      provider: codebuild
      properties:
        environment_variables:
          TERRAFORM_VERSION: "0.14.10" # terraform version
    deploy:
      provider: codebuild
      properties:
        image: "STANDARD_5_0"
        environment_variables:
          TARGET_ACCOUNTS: 111111111111,222222222222 # target accounts
          TARGET_OUS: /core/infrastructure,/sandbox # target OUs
          MASTER_ACCOUNT_ID: 333333333333 # master account
          REGIONS: eu-west-1 # target regions
  params:
    restart_execution_on_update: true
  targets:
    - name: terraform-scan # optional
      properties:
        spec_filename: tf_scan.yml # terraform scan
    - name: terraform-plan
      properties:
        spec_filename: tf_plan.yml # terraform plan
    - approval # manual approval
    - name: terraform-apply
      properties:
        spec_filename: tf_apply.yml # terraform apply
```

2. Add the project name in params/global.yml file
3. Add terraform code to the `tf` folder. Do not make changes to `backend.tf` file and `main.tf`.
4. Add variable definition to tf\variables.tf file and variable values to tfvars/global.auto.tfvars

   - Local variables (per account) can be configured using the following naming convention

     ```
     tfvars <-- This folder contains the structure to define terraform variables
     │
     └───global.auto.tfvars <-- this file contains global variables applied to all the target accounts
     │
     └───111111111111 <-- this folders contains variable files related to account 111111111111
     │   └──────│   local.auto.tfvars <-- this file contains variables related to account 111111111111
     │
     └───222222222222 <-- this folders contains variable files related to account 222222222222
         └──────│   local.auto.tfvars <-- this file contains variables related to account 222222222222
     ```

5. Push to sample-terraform ADF repository
6. Pipeline contains a manual step approval between terraform plan and terraform apply. Confirm to proceed.
