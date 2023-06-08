# ADF Account Provisioning

This directory contains `.yml` file(s) that will make up your AWS Account
ecosystem. This Account Provisioning process is a declarative approach to
defining AWS Accounts along with where they will live within your AWS
Organization. This process enables to end-to-end bootstrapping and associated
pipeline generation for new AWS Accounts and is the recommended way to provision
and setup AWS Accounts via ADF.

**Note on Provisioning AWS Accounts via AWS ControlTower**
ADF is fully compatible with [AWS ControlTower](https://aws.amazon.com/de/controltower/).
If you deployed ADF and AWS ControlTower in your AWS Organization and if you opted for 
vending AWS Accounts via AWS ControlTower, you can ignore the ADF Account Provisioning 
feature. 

## Overview

When setting ADF for the first time you will have an auto-generated `adf.yml`
file within the *adf-accounts* folder. This is processed by the bootstrap
process to ensure the deployment account exists and is in the Organizational
unit that corresponds to the definition (*/deployment*).

For creating additional accounts, you can create any `.yml` file within the
*adf-accounts* folder. This will be processed and the accounts will be created
and moved into the desired OU.

The OU name is the name of the direct parent of the account. If you want to move
an account to the root you can provide the AWS organization id (e.g., `r-abc1`).
If you are dealing with nested organizational units you can separate them with
a `/` (see examples above).

### Current Features

- Create new AWS accounts within existing AWS Organization.
- Move accounts to the organizational unit defined in config file(s).
- Optionally remove default VPCs and related resources on each region.
- Create and update account alias.
- Account tagging.
- Allow the account access to view its own billing.
- Set up support subscriptions during account provisioning

### Currently not supported

- Updating account names
- Updating account email addresses
- Removing accounts
- Handling root account credentials and MFA
- Changing the support subscription of an account.

### Configuration Parameters

- `account_full_name`: AWS account name
- `organizational_unit_path`: Path to the OU within AWS Organizations.
  OUs are divided by `/`, e.g., `ou-l1/ou-l2/ou-l3`
- `email`: Email associated by the account, must be valid otherwise it is not
  possible to access as root user when needed.
- `delete_default_vpc`: `True|False` if Default VPCs need to be delete from all
  AWS Regions.
- `allow_billing`: `True|False` if the account see its own costs within the
  organization.
- `support_level`: `basic|enterprise` ADF will raise a ticket to add the account
  to an existing AWS support subscription when an account is created.
  Currently ADF only supports basic or enterprise.
  **NB: This is for activating enterprise support on account creation only.
  As a prerequisite your organization management account must already have
  enterprise support activated.**
- `alias`: AWS account alias. Must be unique globally otherwise cannot be
  created. Check [here](https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html)
  for further details. If the account alias is not created or already exists,
  in the Federation login page, no alias will be presented.
- `tags`: list of tags associate to the account.

### Examples

You can create as many `.yml` files as required and split them up into groups as
required. As mentioned above, when deploying ADF initially you will get an
`adf.yml` file which will hold the information for the initial deployment
account. If you are upgrading from a previous version of ADF you may need to
create the `adf.yml` yourself if you want to manage the deployment account
itself via ADF. You can create other files to create the structure you desire,
as an example, we might create a `prod.yml` and `test.yml` which hold their
respective environments AWS Accounts.

#### prod.yml

```yaml
accounts:
  - account_full_name: company-prod-1
    organizational_unit_path: /business-unit1/prod
    email: prod-team-1@example.com
    allow_billing: False
    delete_default_vpc: True
    support_level: enterprise
    alias: prod-company-1
    tags:
      - created_by: adf
      - environment: prod
      - costcenter: 123
```

#### test.yml

```yaml
accounts:
  - account_full_name: company-test-1
    organizational_unit_path: /business-unit1/test
    email: test-team-1@example.com
    allow_billing: True
    delete_default_vpc: False
    support_level: basic
    alias: test-company-11
    tags:
      - created_by: adf
      - environment: test
      - costcenter: 123

  - account_full_name: company-test-2
    organizational_unit_path: /business-unit1/test
    email: test-team-2@example.com
    allow_billing: True
    delete_default_vpc: False
    alias: test-company-12
    tags:
      - created_by: adf
      - environment: test
      - costcenter: 123
```

When the bootstrap pipeline runs it will check to see if these accounts
already exist in the Organization, if they do it will ensure the tags and
alias' are correct and continue on. If they do not exist, ADF will call the
Organizations API to create these accounts and move them into the correct OU
*(thus starting the bootstrap process)*.
