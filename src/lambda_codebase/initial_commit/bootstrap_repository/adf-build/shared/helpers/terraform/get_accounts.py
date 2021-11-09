import boto3
import json
import os
from paginator import paginator


sts = boto3.client('sts')

master_acc_id = os.environ["MASTER_ACCOUNT_ID"]
if("TARGET_OUS" in os.environ):
    ou_path = os.environ["TARGET_OUS"]


def list_organizational_units_for_parent(parent_ou):
    organizations = get_boto3_client('organizations', f'arn:aws:sts::{master_acc_id}:role/OrganizationAccountAccessRole-readonly', 'getaccountID')
    organizational_units = [
        ou
        for org_units in organizations.get_paginator("list_organizational_units_for_parent").paginate(ParentId=parent_ou)
        for ou in org_units['OrganizationalUnits']
    ]
    return organizational_units

def get_accounts():
    # Return an array of objects like this: [{'AccountId':'xxx','Email':''}]
    account_details = [] # [{'AccountId':'123','Email':''},{'AccountId':'456','Email':''}]

    print("Master Account ID: " + master_acc_id)
    # Assume a role into the Org Master role to get account ID's and emails
    organizations = get_boto3_client('organizations', f'arn:aws:sts::{master_acc_id}:role/OrganizationAccountAccessRole-readonly', 'getaccountID')
    # organizations = get_boto3_client('organizations', 'arn:aws:sts::' + master_acc_id + ':role/Admin', 'getaccountID')
    for account in paginator(organizations.list_accounts):
        if account['Status'] == 'ACTIVE':
            account_details.append({
                'AccountId': account['Id'],
                'Email': account['Email']
            })
    return account_details

def get_accounts_from_ous():
    parent_ou_id = None
    account_list = []
    organizations = get_boto3_client('organizations', f'arn:aws:sts::{master_acc_id}:role/OrganizationAccountAccessRole-readonly', 'getaccountID')
    # Read organization root id
    root_ids = []
    for id in paginator(organizations.list_roots):
            root_ids.append({
                'AccountId': id['Id']
            })
    root_id = root_ids[0]['AccountId'] 
    print("Target OUs")
    for path in ou_path.split(','):
        print(path)
        # Set initial OU to start looking for given ou_path
        if parent_ou_id is None:
            parent_ou_id = root_id

        # Parse ou_path and find the ID
        ou_hierarchy = path.strip('/').split('/')
        hierarchy_index = 0
        if(path.strip() == '/'):
            account_list.extend(get_account_recursive(organizations, parent_ou_id, '/'))
        else:
            while hierarchy_index < len(ou_hierarchy):
                org_units = list_organizational_units_for_parent(parent_ou_id)
                for ou in org_units:
                    if ou['Name'] == ou_hierarchy[hierarchy_index]:
                        parent_ou_id = ou['Id']
                        hierarchy_index += 1
                        break
                else:
                    raise ValueError(f'Could not find ou with name {ou_hierarchy} in OU list {org_units}.')

            account_list.extend(get_account_recursive(organizations, parent_ou_id, '/'))
        parent_ou_id=None
    print("Account list: ", end = '')
    for i in account_list:
        print(i['AccountId'] + " ", end = '')
    print()
    print("Number of target accounts: " + str(len(account_list)))
    return account_list


def get_boto3_client(service, role, session_name):
    role = sts.assume_role(
            RoleArn=role,
            RoleSessionName=session_name,
            DurationSeconds=900
        )
    session = boto3.Session(
            aws_access_key_id=role['Credentials']['AccessKeyId'],
            aws_secret_access_key=role['Credentials']['SecretAccessKey'],
            aws_session_token=role['Credentials']['SessionToken']
        )
    return session.client(service)

def get_account_recursive(org_client: boto3.client, ou_id: str, path: str) -> list:
    account_list = []
    # Get OUs
    paginator = org_client.get_paginator('list_children')
    pages = paginator.paginate(
        ParentId=ou_id,
        ChildType='ORGANIZATIONAL_UNIT'
    )
    for page in pages:
        for child in page['Children']:
            account_list.extend(get_account_recursive(org_client, child['Id'], path+ou_id+'/'))

    # Get Accounts
    pages = paginator.paginate(
        ParentId=ou_id,
        ChildType='ACCOUNT'
    )
    for page in pages:
        for child in page['Children']:
            account_list.append({
                'AccountId': child['Id']
            })
    return account_list


accounts = get_accounts()
with open('accounts.json', 'w') as outfile:
    json.dump(accounts, outfile)

if("TARGET_OUS" in os.environ):
    accounts_from_ous = get_accounts_from_ous()
    with open('accounts_from_ous.json', 'w') as outfile:
        json.dump(accounts_from_ous, outfile)