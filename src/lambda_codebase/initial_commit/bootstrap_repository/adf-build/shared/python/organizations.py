# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Organizations module used throughout the ADF
"""

import json

from botocore.config import Config
from botocore.exceptions import ClientError
from errors import RootOUIDError
from logger import configure_logger
from paginator import paginator

LOGGER = configure_logger(__name__)


class Organizations: # pylint: disable=R0904
    """Class used for modeling Organizations
    """

    _config = Config(retries=dict(max_attempts=30))

    def __init__(self, role, account_id=None):
        self.client = role.client(
            'organizations',
            config=Organizations._config)
        self.account_id = account_id
        self.account_ids = []
        self.root_id = None

    def get_parent_info(self):
        response = self.list_parents(self.account_id)
        return {
            "ou_parent_id": response.get('Id'),
            "ou_parent_type": response.get('Type')
        }

    def enable_scp(self):
        try:
            self.client.enable_policy_type(
                RootId=self.get_ou_root_id(),
                PolicyType='SERVICE_CONTROL_POLICY'
            )
        except self.client.exceptions.PolicyTypeAlreadyEnabledException:
            LOGGER.info('SCPs are currently enabled within the Organization')

    @staticmethod
    def trim_scp_path(scp):
        return scp[2:] if scp.startswith('//') else scp

    def get_organization_map(self, org_structure, counter=0):
        for name, ou_id in org_structure.copy().items():
            for organization_id in [organization_id['Id'] for organization_id in paginator(self.client.list_children, **{"ParentId":ou_id, "ChildType":"ORGANIZATIONAL_UNIT"})]:
                if organization_id in org_structure.values() and counter != 0:
                    continue
                ou_name = self.describe_ou_name(organization_id)
                trimmed_path = Organizations.trim_scp_path("{0}/{1}".format(name, ou_name))
                org_structure[trimmed_path] = organization_id
        counter = counter + 1
        # Counter is greater than 4 here is the conditional as organizations cannot have more than 5 levels of nested OUs
        return org_structure if counter > 4 else self.get_organization_map(org_structure, counter)

    def update_scp(self, content, policy_id):
        self.client.update_policy(
            PolicyId=policy_id,
            Content=content
        )

    def create_scp(self, content, ou_path):
        response = self.client.create_policy(
            Content=content,
            Description='ADF Managed Service Control Policy',
            Name='adf-scp-{0}'.format(ou_path),
            Type='SERVICE_CONTROL_POLICY'
        )
        return response['Policy']['PolicySummary']['Id']

    @staticmethod
    def get_scp_body(path):
        with open(path, 'r') as scp:
            return json.dumps(json.load(scp))

    def list_scps(self, name):
        response = list(paginator(self.client.list_policies, Filter="SERVICE_CONTROL_POLICY"))
        try:
            return [policy for policy in response if policy['Name'] == name][0]['Id']
        except IndexError:
            return []

    def describe_scp_id_for_target(self, target_id):
        response = self.client.list_policies_for_target(
            TargetId=target_id,
            Filter='SERVICE_CONTROL_POLICY'
        )
        try:
            return [p for p in response['Policies'] if p['Description'] == 'ADF Managed Service Control Policy'][0]['Id']
        except IndexError:
            return []

    def describe_scp(self, policy_id):
        response = self.client.describe_policy(
            PolicyId=policy_id
        )
        return response.get('Policy')

    def attach_scp(self, policy_id, target_id):
        self.client.attach_policy(
            PolicyId=policy_id,
            TargetId=target_id
        )

    def detach_scp(self, policy_id, target_id):
        self.client.detach_policy(
            PolicyId=policy_id,
            TargetId=target_id
        )

    def delete_scp(self, policy_id):
        self.client.delete_policy(
            PolicyId=policy_id
        )

    def get_account_ids(self):
        for account in paginator(self.client.list_accounts):
            if not account.get('Status') == 'ACTIVE':
                LOGGER.warning('Account %s is not an Active AWS Account', account['Id'])
                continue
            self.account_ids.append(account['Id'])
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
        except ClientError:
            raise RootOUIDError("OU is the Root of the Organization")

    @staticmethod
    def determine_ou_path(ou_path, ou_child_name):
        return '{0}/{1}'.format(ou_path,
                                ou_child_name) if ou_path else ou_child_name

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
                raise Exception(
                    "Path {0} failed to return a child OU at '{1}'".format(
                        path, p[0]))
        else: # pylint: disable=W0120
            return self.get_accounts_for_parent(ou_id)

    def build_account_path(self, ou_id, account_path, cache):
        """Builds a path tree to the account from the root of the Organization
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
