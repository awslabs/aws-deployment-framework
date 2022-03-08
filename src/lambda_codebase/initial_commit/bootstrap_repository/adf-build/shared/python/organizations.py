# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations module used throughout the ADF
"""

import json
import os

from time import sleep
from botocore.config import Config
from botocore.exceptions import ClientError

from errors import RootOUIDError
from logger import configure_logger
from paginator import paginator

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv('AWS_REGION')


class Organizations:  # pylint: disable=R0904
    """
    Class used for modeling Organizations
    """

    _config = Config(retries=dict(max_attempts=30))

    def __init__(self, role, account_id=None):
        self.client = role.client(
            'organizations',
            config=Organizations._config
        )
        self.tags_client = role.client(
            'resourcegroupstaggingapi',
            region_name=REGION_DEFAULT,
            config=Organizations._config
        )
        self.account_id = account_id
        self.account_ids = []
        self.root_id = None

    def get_parent_info(self):
        response = self.list_parents(self.account_id)
        return {
            "ou_parent_id": response.get('Id'),
            "ou_parent_type": response.get('Type')
        }

    def enable_organization_policies(self, policy_type='SERVICE_CONTROL_POLICY'):  # or 'TAG_POLICY'
        try:
            self.client.enable_policy_type(
                RootId=self.get_ou_root_id(),
                PolicyType=policy_type
            )
        except self.client.exceptions.PolicyTypeAlreadyEnabledException:
            LOGGER.info('%s are currently enabled within the Organization', policy_type)

    @staticmethod
    def trim_policy_path(policy):
        return policy[2:] if policy.startswith('//') else policy

    @staticmethod
    def is_ou_id(ou_id):
        return ou_id[0] in ['r','o']

    def get_organization_map(self, org_structure, counter=0):
        for name, ou_id in org_structure.copy().items():
            # Skip accounts - accounts can't have children
            if not Organizations.is_ou_id(ou_id):
                continue
            # List OUs
            for organization_id in [organization_id['Id'] for organization_id in paginator(self.client.list_children, **{"ParentId":ou_id, "ChildType":"ORGANIZATIONAL_UNIT"})]:
                if organization_id in org_structure.values() and counter != 0:
                    continue
                ou_name = self.describe_ou_name(organization_id)
                trimmed_path = Organizations.trim_policy_path(f"{name}/{ou_name}")
                org_structure[trimmed_path] = organization_id
            # List accounts
            for account_id in [account_id['Id'] for account_id in paginator(self.client.list_children, **{"ParentId":ou_id, "ChildType":"ACCOUNT"})]:
                if account_id in org_structure.values() and counter != 0:
                    continue
                account_name = self.describe_account_name(account_id)
                trimmed_path = Organizations.trim_policy_path(f"{name}/{account_name}")
                org_structure[trimmed_path] = account_id
        counter = counter + 1
        # Counter is greater than 5 here is the conditional as organizations cannot have more than 5 levels of nested OUs + 1 accounts "level"
        return org_structure if counter > 5 else self.get_organization_map(org_structure, counter)

    def update_policy(self, content, policy_id):
        self.client.update_policy(
            PolicyId=policy_id,
            Content=content
        )

    def create_policy(self, content, ou_path, policy_type="SERVICE_CONTROL_POLICY"):
        policy_type_name = (
            'scp' if policy_type == "SERVICE_CONTROL_POLICY"
            else 'tagging-policy'
        )
        response = self.client.create_policy(
            Content=content,
            Description=f'ADF Managed {policy_type}',
            Name=f'adf-{policy_type_name}-{ou_path}',
            Type=policy_type
        )
        return response['Policy']['PolicySummary']['Id']

    @staticmethod
    def get_policy_body(path):
        with open(f'./adf-bootstrap/{path}', mode='r', encoding='utf-8') as policy:
            return json.dumps(json.load(policy))

    def list_policies(self, name, policy_type="SERVICE_CONTROL_POLICY"):
        response = list(paginator(self.client.list_policies, Filter=policy_type))
        try:
            return [policy for policy in response if policy['Name'] == name][0]['Id']
        except IndexError:
            return []

    def describe_policy_id_for_target(self, target_id, policy_type='SERVICE_CONTROL_POLICY'):
        response = self.client.list_policies_for_target(
            TargetId=target_id,
            Filter=policy_type
        )
        try:
            return [p for p in response['Policies'] if f'ADF Managed {policy_type}' in p['Description']][0]['Id']
        except IndexError:
            return []

    def describe_policy(self, policy_id):
        response = self.client.describe_policy(
            PolicyId=policy_id
        )
        return response.get('Policy')

    def attach_policy(self, policy_id, target_id):
        try:
            self.client.attach_policy(
                PolicyId=policy_id,
                TargetId=target_id
            )
        except self.client.exceptions.DuplicatePolicyAttachmentException:
            pass

    def detach_policy(self, policy_id, target_id):
        self.client.detach_policy(
            PolicyId=policy_id,
            TargetId=target_id
        )

    def delete_policy(self, policy_id):
        self.client.delete_policy(
            PolicyId=policy_id
        )


    def get_accounts(self):
        for account in paginator(self.client.list_accounts):
            if not account.get('Status') == 'ACTIVE':
                LOGGER.warning('Account %s is not an Active AWS Account', account['Id'])
                continue
            self.account_ids.append(account)
        return self.account_ids

    def get_organization_info(self):
        response = self.client.describe_organization()
        return {
            "organization_master_account_id": response.get(
                'Organization').get(
                    'MasterAccountId'
                ),
            "organization_id": response.get('Organization').get('Id'),
            "feature_set": response.get('Organization').get('FeatureSet')
        }

    def describe_ou_name(self, ou_id):
        try:
            response = self.client.describe_organizational_unit(
                OrganizationalUnitId=ou_id
            )
            return response['OrganizationalUnit']['Name']
        except ClientError as error:
            raise RootOUIDError("OU is the Root of the Organization") from error

    def describe_account_name(self, account_id):
        try:
            response = self.client.describe_account(
                AccountId=account_id
            )
            return response['Account']['Name']
        except ClientError as error:
            LOGGER.error('Failed to retrieve account name for account ID %s', account_id)
            raise error

    @staticmethod
    def determine_ou_path(ou_path, ou_child_name):
        return f'{ou_path}/{ou_child_name}' if ou_path else ou_child_name

    def list_parents(self, ou_id):
        return self.client.list_parents(
            ChildId=ou_id
        ).get('Parents')[0]

    def get_accounts_for_parent(self, parent_id):
        return paginator(
            self.client.list_accounts_for_parent,
            ParentId=parent_id
        )

    def get_child_ous(self, parent_id):
        return paginator(
            self.client.list_organizational_units_for_parent,
            ParentId=parent_id
        )

    def get_ou_root_id(self):
        return self.client.list_roots().get('Roots')[0].get('Id')

    def dir_to_ou(self, path):
        p = path.split('/')[1:]
        ou_id = self.get_ou_root_id()

        while p:
            for ou in self.get_child_ous(ou_id):
                if ou['Name'] == p[0]:
                    p.pop(0)
                    ou_id = ou['Id']
                    break
            else:
                raise Exception(f"Path {path} failed to return a child OU at '{p[0]}'")
        else: # pylint: disable=W0120
            return self.get_accounts_for_parent(ou_id)

    def build_account_path(self, ou_id, account_path, cache):
        """
        Builds a path tree to the account from the root of the Organization
        """
        current = self.list_parents(ou_id)

        # While not at the root of the Organization
        while current.get('Type') != "ROOT":
            # check cache for ou name of id
            if not cache.check(current.get('Id')):
                cache.add(
                    current.get('Id'),
                    self.describe_ou_name(
                        current.get('Id')))
            ou_name = cache.check(current.get('Id'))
            account_path.append(ou_name)
            return self.build_account_path(
                current.get('Id'),
                account_path,
                cache
            )
        return Organizations.determine_ou_path(
            '/'.join(list(reversed(account_path))),
            self.describe_ou_name(
                self.get_parent_info().get("ou_parent_id")
            )
        )

    def get_account_ids_for_tags(self, tags):
        tag_filter = []
        for key, value in tags.items():
            if isinstance(value, list):
                values = value
            else:
                values = [value]
            tag_filter.append({'Key': key, 'Values': values})
        account_ids = []
        for resource in paginator(self.tags_client.get_resources, TagFilters=tag_filter, ResourceTypeFilters=['organizations']):
            arn = resource['ResourceARN']
            account_id = arn.split('/')[::-1][0]
            account_ids.append(account_id)
        return account_ids

    def list_organizational_units_for_parent(self, parent_ou):
        organizational_units = [
            ou
            for org_units in self.client.get_paginator("list_organizational_units_for_parent").paginate(ParentId=parent_ou)
            for ou in org_units['OrganizationalUnits']
        ]
        return organizational_units

    def get_account_id(self, account_name):
        for account in self.list_accounts():
            if account["Name"].strip() == account_name.strip():
                return account['Id']

        return None

    def list_accounts(self):
        """
        Retrieves all accounts in organization.
        """
        existing_accounts = [
            account
            for accounts in self.client.get_paginator("list_accounts").paginate()
            for account in accounts['Accounts']
        ]
        return existing_accounts

    def get_ou_id(self, ou_path, parent_ou_id=None):
        # Return root OU if '/' is provided
        if ou_path.strip() == '/':
            return self.root_id

        # Set initial OU to start looking for given ou_path
        if parent_ou_id is None:
            parent_ou_id = self.root_id

        # Parse ou_path and find the ID
        ou_hierarchy = ou_path.strip('/').split('/')
        hierarchy_index = 0

        while hierarchy_index < len(ou_hierarchy):
            org_units = self.list_organizational_units_for_parent(parent_ou_id)
            for ou in org_units:
                if ou['Name'] == ou_hierarchy[hierarchy_index]:
                    parent_ou_id = ou['Id']
                    hierarchy_index += 1
                    break
            else:
                raise ValueError(f'Could not find ou with name {ou_hierarchy} in OU list {org_units}.')

        return parent_ou_id

    def move_account(self, account_id, ou_path):
        self.root_id = self.get_ou_root_id()
        ou_id = self.get_ou_id(ou_path)
        response = self.client.list_parents(ChildId=account_id)
        source_parent_id = response['Parents'][0]['Id']

        if source_parent_id == ou_id:
            # Account is already resided in ou_path
            return

        response = self.client.move_account(
            AccountId=account_id,
            SourceParentId=source_parent_id,
            DestinationParentId=ou_id
        )

    def create_account_tags(self, account_id, tags):
        formatted_tags = [
            {'Key': str(key), 'Value': str(value)}
            for tag in tags
            for key, value in tag.items()
        ]
        self.client.tag_resource(
            ResourceId=account_id,
            Tags=formatted_tags
        )

    @staticmethod
    def create_account_alias(account_alias, role):
        iam_client = role.client('iam')
        try:
            iam_client.create_account_alias(AccountAlias=account_alias)
        except iam_client.exceptions.EntityAlreadyExistsException:
            pass  # Alias already exists

    def create_account(self, account, adf_role_name):
        allow_billing = "ALLOW" if account.allow_billing else "DENY"
        response = self.client.create_account(
            Email=account.email,
            AccountName=account.full_name,
            RoleName=adf_role_name,  # defaults to OrganizationAccountAccessRole
            IamUserAccessToBilling=allow_billing,
        )["CreateAccountStatus"]
        while response["State"] == "IN_PROGRESS":
            response = self.client.describe_create_account_status(
                CreateAccountRequestId=response["Id"]
            )["CreateAccountStatus"]

            if response.get("FailureReason"):
                raise IOError(
                    f"Failed to create account {account.full_name}: {response['FailureReason']}"
                )
            sleep(5)  # waiting for 5 sec before checking account status again
        account_id = response["AccountId"]
        # TODO: Instead of sleeping, query for the role.
        sleep(90)  # Wait 90 sec until OrganizationalRole is created in new account (Temp solution)

        return account_id
