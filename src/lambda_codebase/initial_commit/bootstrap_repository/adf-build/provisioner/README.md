# Accounts

## Overview

This repository contains code that manages the process around AWS account creation. It assumes you are working with the [AWS Deployment Framework](https://github.com/awslabs/aws-deployment-framework) for managing deployments in a multi-account AWS organization.

### Current Features

- Create new AWS accounts within existing AWS Organization
- Move accounts to the organizational unit defined in config files
- Optionally remove default VPCs and related resources on each region
- Create and update account alias
- Account tagging
- Optional protection from moving accounts directly between organizational units (related to AWS Deployment Framework)

### Not supported due to AWS Organization API limitations

- Updating account names
- Updating account email addresses
- Removing accounts
- Handling root account credentials and MFA

## Installation

### ADF Organization role in master account

In order to grant master accounts ADF role to delete default VPC and create account alias within Organizations it is necessary to add to the `bootstrap` repository in `adf-build/global.yml` the following rights to the `OrganizationsPolicy` resource:

```yaml
- Effect: Allow
  Action:
    - organizations:*
  Resource: "*"
- Effect: Allow
  Action:
    - sts:AssumeRole
  Resource: "*"
- Effect: Allow
  Action:
    - ec2:Describe*
    - ec2:Delete*
    - ec2:Detach*
  Resource: "*"
- Effect: Allow
  Action:
    - iam:CreateAccountAlias
    - config:DeleteConfigurationRecorder
    - config:DeleteDeliveryChannel
  Resource: "*"
```

Furthermore we need to add ADF Deployment account id as trusted relationship for the `OrganizationsRole`:

```yaml
OrganizationsRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Ref CrossAccountAccessRole
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            AWS:
              - !Ref AWS::AccountId
              - !Ref DeploymentAccountId # add this to grant deployment account the right to assume this role
          Action:
            - sts:AssumeRole
```

### ADF CodeBuild role

As for master account, the deployment accounts need an additional grant to run the build phase of the pipeline. Therefore it is necessary to add to the `bootstrap` repository in `deployment/global.yml` the following rights to the `CodeBuildRolePolicy` resource:

```yaml
- ec2:DescribeRegions
- organizations:DescribeOrganization
```

and

```yaml
- Effect: Allow
  Action:
    - "sts:AssumeRole"
  Resource: !Sub "arn:aws:iam::${MasterAccountId}:role/${CrossAccountAccessRole}"
```

### ADF Pipeline

Create a pipeline in the `deplyoment-map.yml` with a `cc-buildonly` type as below:

```yaml
  - name: accounts
    type: cc-buildonly
    params:
      - SourceAccountId: 12345678912
      - NotificationEndpoint: mynotification@mydomain.com
      - ScheduleExpression: rate(24 hours)
```

Then, in the `buildspec.yml` modify the `ORG_ID` parameter with your root id, you can find it in the ARN of the root in AWS Organizations. It is the `r-WXYZ` code in the full ARN (e.g., `arn:aws:organizations::12345678912:root/o-qu1EXAMPLEcyr/r-84hh`).

## Configuration

Next define configuration files for the accounts you would like to manage. The default location the script looks for these config files is `/config`. You can have multiple configuration files for logical separation. The script will iterate and validate each file before sequentially creating/updating the defined accounts.

Here is an example file:

```yaml
Accounts:
  # Account with only mandatory parameters
  - AccountFullName: playgroundaccount
    OrganizationalUnitPath: playground/
    Email: playgroundaccountmydomain.com

  # Delete the default VPC for this account
  - AccountFullName: usdevaccount
    OrganizationalUnitPath: us/dev
    Email: usdevaccountmydomain.com
    DeleteDefaultVPC: True

  # Account with all available parameters
  - AccountFullName: myrootaccount
    OrganizationalUnitPath: r-abc1
    Email: myrootaccountmydomain.com
    DeleteDefaultVPC: True
    AllowDirectMoveBetweenOU: True
    Alias: i-dont-want-my-alias-to-be-the-same-as-the-account-full-name
    AllowBilling: False
    Tags:
      - CostCenter: 123456789
      - OU: us/dev
      - Billing: enabled
```

To create new accounts or to move accounts to a different OU you only have to update the relevant account config file in the `/config` folder and re-run the pipeline.

The OU name is the name of the direct parent of the account. If you want to move an account to the root you can provide the AWS organization id (e.g., `r-abc1`). If you are dealing with nested organizational units you can separate them with a / (see examples above).

### Configuration parameters

- `AccountFullName`: AWS account name
- `OrganizationalUnitPath`: Path to the OU within AWS Organizations. OUs are divided by /, e.g., `ou-l1/ou-l2/ou-l3`
- `Email`: Email associated by the account, must be valid otherwise it is not possible to access as root user when needed
- `DeleteDefaultVPC`: `True|False` if Default VPCs need to be delete from all AWS Regions
- `AllowDirectMoveBetweenOU`: `True|False` if the account can be move from OU to OU without passing by the root level of AWS Organizations (check ADF documentation for related consequences)
- `AllowBilling`: `True|False` if the account see its own costs within the organization
- `Alias`: AWS account alias. Must be unique globally otherwise cannot be created. Check https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html for further details. If the account alias is not created or already exists, in the Federation login page, no alias will be presented
- `Tags`: list of tags associate to the account
