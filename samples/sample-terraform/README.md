# Terraform template

## Overview

This repository contains a module that manage the deployment of terraform code to multiple accounts and regions.
The module consists of four build stages defined in the following file:

- `buildspec.yml`: install the version of terraform specified in the pipeline configuration
- `tf_scan.yml`: (optional) scans for vulnerabilities in the terraform code using the terrascan application. If vulnerabilities are found, it will fail and block further execution in the pipeline. It is recommended to enable this step in all ADF terraform pipelines.
- `tf_plan.yml`: get the list of accounts from the organization and run a terraform plan
- `tf_apply.yml`: get the list of accounts from the organization and run a terraform plan and apply

An optional approval step could be added between plan and apply as shown in the pipeline definition below.

## Parameters

- TERRAFORM_VERSION: the terraform version used to deploy the resource
- TARGET_ACCOUNTS: comma separated list of target accounts
- TARGET_OUS: comma separated list of target leaf OUs (parent OUs are supported)
- REGIONS: comma separated list of target regions. If this parameter is empty, the main ADF region is used.

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
          MANAGEMENT_ACCOUNT_ID: 333333333333  # management account / billing account
          REGIONS: eu-west-1 # target regions. Add a comma separated list to define multiple regions e.g. eu-west-1,us-east-1
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

Terraform state files are stored in the regional S3 buckets in the deployment account. One state file per account/region/module is created
e.g. Project name: sample-tf-module
Target accounts: 111111111111, 222222222222
Target regions: eu-west-1 (main ADF region), us-east-1
The following state files are created

- 111111111111 main region (eu-west-1) adf-global-base-deployment-pipelinebucketxyz/sample-tf-module/111111111111.tfstate
- 111111111111 secondary region (us-east-1) adf-regional-base-deploy-deploymentframeworkregio-jsm/sample-tf-module/111111111111.tfstate
- 222222222222 main region (eu-west-1) adf-global-base-deployment-pipelinebucketxyz/sample-tf-module/222222222222.tfstate
- 222222222222 secondary region (us-east-1) adf-regional-base-deploy-deploymentframeworkregio-jsm/sample-tf-module/222222222222.tfstate

A DynamoDB table manage the lock of the state file. It is deployed in every ADF regions named adf_locktable
