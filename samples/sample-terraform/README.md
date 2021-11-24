# Terraform template

**Overview**

ADF support the deployment of Terraform code to multiple accounts and regions through Terraform pipelines.
The module consists of four build stages defined in the following CodeBuild build specification:

- `buildspec.yml`: install the version of Terraform specified in the pipeline configuration.
- `tf_scan.yml`: (optional) scans for vulnerabilities in the terraform code using the terrascan application. If vulnerabilities are found, it will fail and block further execution in the pipeline. It is recommended to enable this step in all ADF terraform pipelines.
- `tf_plan.yml`: get the list of accounts from the organization and run a terraform plan.
- `tf_apply.yml`: get the list of accounts from the organization and run a terraform plan and apply.

An optional approval step could be added between plan and apply as shown in the pipeline definition below.

**Parameters**

- `TERRAFORM_VERSION`: the Terraform version used to deploy the resource. This parameter must be defined in the `buildspec.yml` file of the repository.
- `TARGET_ACCOUNTS`: comma separated list of target accounts.
- `TARGET_OUS`: comma separated list of target leaf OUs (parent OUs are supported).
- `REGIONS`: comma separated list of target regions. If this parameter is empty, the main ADF region is used.
- `MANAGEMENT_ACCOUNT_ID`: id of the AWS Organizations management account.

## Deployment procedure

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
    deploy:
      provider: codebuild
      properties:
        image: "STANDARD_5_0"
        environment_variables:
          TARGET_ACCOUNTS: 111111111111,222222222222 # target accounts
          TARGET_OUS: /core/infrastructure,/sandbox # target OUs
          MANAGEMENT_ACCOUNT_ID: 333333333333 # management account / billing account
          REGIONS: eu-west-1 # target regions. Add a comma separated list to define multiple regions e.g. eu-west-1,us-east-1
  targets:
    - name: terraform-scan # optional
      properties:
        spec_filename: tf_scan.yml # Terraform scan
    - name: terraform-plan
      properties:
        spec_filename: tf_plan.yml # Terraform plan
    - approval # manual approval
    - name: terraform-apply
      properties:
        spec_filename: tf_apply.yml # Terraform apply
```

2. Add the project name in `params/global.yml` file.
3. Add Terraform code to the `tf` folder. Do not make changes to `backend.tf` file and `main.tf` which contain the definition of the remote state file location, Terraform provider definition. Any change to these files could affect the standard functionalities of this module.
4. Add variable definition to `tf/variables.tf` file and variable values to `tfvars/global.auto.tfvars`.

   - Local variables (per account) can be configured using the following naming convention:

     ```
     tfvars <-- This folder contains the structure to define Terraform variables
     │
     └───global.auto.tfvars <-- this file contains global variables applied to all the target accounts
     │
     └───111111111111 <-- this folders contains variable files related to account 111111111111
     │   └──────│   local.auto.tfvars <-- this file contains variables related to account 111111111111
     │
     └───222222222222 <-- this folders contains variable files related to account 222222222222
         └──────│   local.auto.tfvars <-- this file contains variables related to account 222222222222
     ```

5. Define the desired `TERRAFORM_VERSION` in the `buildspec.yml` file as shown in the sample-terraform example. ADF supports Terraform version v0.13.0 and later.
6. Push to your Terraform ADF repository, for example the sample-terraform one.
7. Pipeline contains a manual approval step between Terraform plan and Terraform apply. Confirm to proceed.

Terraform state files are stored in the regional S3 buckets in the deployment account. One state file per account/region/module is created.

e.g.

- Project name: sample-tf-module
- Target accounts: 111111111111, 222222222222
- Target regions: eu-west-1 (main ADF region), us-east-1

The following state files are created:

- 111111111111 main region (eu-west-1) adf-global-base-deployment-pipelinebucketxyz/sample-tf-module/111111111111.tfstate
- 111111111111 secondary region (us-east-1) adf-regional-base-deploy-deploymentframeworkregio-jsm/sample-tf-module/111111111111.tfstate
- 222222222222 main region (eu-west-1) adf-global-base-deployment-pipelinebucketxyz/sample-tf-module/222222222222.tfstate
- 222222222222 secondary region (us-east-1) adf-regional-base-deploy-deploymentframeworkregio-jsm/sample-tf-module/222222222222.tfstate

A DynamoDB table is created to manage the lock of the state file. It is deployed in every ADF regions named `adf_locktable`. **Please note**: usage of this locking table is charged on the deployment account.
