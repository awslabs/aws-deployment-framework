# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Organizations module used throughout the ADF
"""

from botocore.config import Config
from logger import configure_logger
from paginator import paginator

LOGGER = configure_logger(__name__)


class Organizations:
    """Class used for modeling Organizations
    """

    _config = Config(retries=dict(max_attempts=30))

    def __init__(self, role, account_id=None):
        self.client = role.client(
            'organizations',
            config=Organizations._config)
        self.account_id = account_id
        self.account_ids = []

    def get_parent_info(self):
        response = self.list_parents(self.account_id)
        return {
            "ou_parent_id": response.get('Id'),
            "ou_parent_type": response.get('Type')
        }

    def get_account_ids(self):
        for account in paginator(self.client.list_accounts):
            if account.get('Status') == 'ACTIVE':
                self.account_ids.append(account['Id'])

        return self.account_ids

    def get_organization_info(self):
        response = self.client.describe_organization()
        return {
            "organization_master_account_id": response.get(
                'Organization').get(
                    'MasterAccountId'
                ),
            "organization_id": response.get('Organization').get('Id')
        }

    def describe_ou_name(self, ou_id):
        try:
            response = self.client.describe_organizational_unit(
                OrganizationalUnitId=ou_id
            )
            return response['OrganizationalUnit']['Name']
        except KeyError:
            return "ROOT"

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

    def dir_to_ou(self, path):
        p = path.split('/')[1:]
        ou_id = self.client.list_roots().get('Roots')[0].get('Id')

        while p:
            for ou in self.get_child_ous(ou_id):
                if ou['Name'] == p[0]:
                    p.pop(0)
                    ou_id = ou['Id']
                    break
            else:
                raise Exception(
                    "Path {} failed to return a child OU at '{}'".format(
                        path, p[0]))
        else:  # pylint: disable=W0120
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
