# ADF Account Provisionion

This directory contains *.yml* file(s) that will make up your AWS Account ecosystem. This Account Provisioning process is a declarative approach to defining AWS Accounts along with where they will live within your AWS Organization. This process enables to end-to-end bootstrapping and associated pipeline generation for new AWS Accounts and is the recommended way to provision and setup AWS Accounts via ADF.

## Overview

When setting ADF for the first time you will have an auto-generated *adf.yml* file within the *adf-accounts* folder. This is processed by the bootstrap process to ensure the deployment account exists and is in the Organizational unit that corresponds to the definition (*/deployment*).

For creating additional accounts, you can create any *.yml* file within the *adf-accounts* folder. This will be processed and the accounts will be created and moved into the desired OU.

The OU name is the name of the direct parent of the account. If you want to move an account to the root you can provide the AWS organization id (e.g., `r-abc1`). If you are dealing with nested organizational units you can separate them with a / (see examples above).

### Current Features

- Create new AWS accounts within existing AWS Organization.
- Move accounts to the organizational unit defined in config file(s).
- Optionally remove default VPCs and related resources on each region.
- Create and update account alias.
- Account tagging.
- Allow the account access to view its own billing.

### Currently not supported

- Updating account names
- Updating account email addresses
- Removing accounts
- Handling root account credentials and MFA


### Configuration parameters

- `account_full_name`: AWS account name
- `organizational_unit_path`: Path to the OU within AWS Organizations. OUs are divided by /, e.g., `ou-l1/ou-l2/ou-l3`
- `email`: Email associated by the account, must be valid otherwise it is not possible to access as root user when needed
- `delete_default_vpc`: `True|False` if Default VPCs need to be delete from all AWS Regions.
- `allow_billing`: `True|False` if the account see its own costs within the organization.
- `alias`: AWS account alias. Must be unique globally otherwise cannot be created. Check https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html for further details. If the account alias is not created or already exists, in the Federation login page, no alias will be presented
- `tags`: list of tags associate to the account.
