# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for working with Targets within the Deployment Map.
Targets are the stages/steps within a Pipeline and can
require mutation depending on their structure.
"""

import re


class TargetStructure:
    def __init__(self, target):
        self.target = TargetStructure._define_target_type(target)
        self.account_list = []

    @staticmethod
    def _define_target_type(target):
        if isinstance(target, list):
            output = []
            for t in target:
                output.append({"path": [t]})
            target = output
        if isinstance(target, (int, str)):
            target = [{"path": [target]}]
        if isinstance(target, dict):
            if not isinstance(target.get('path'), list):
                target["path"] = [target.get('path')]

        if not isinstance(target, list):
            target = [target]

        return target


class Target():
    def __init__(self, path, regions, target_structure, organizations):
        self.path = path
        self.regions = [regions] if not isinstance(regions, list) else regions
        self.target_structure = target_structure
        self.organizations = organizations

    @staticmethod
    def _account_is_active(account):
        if account.get('Status') == 'ACTIVE':
            return True
        return False

    def _create_target_info(self, name, account_id):
        return {
            "name": re.sub(r'[^A-Za-z0-9.@\-_]+', '', name),
            "id": account_id,
            "path": self.path,
            "regions": self.regions
        }

    def _target_is_approval(self):
        self.target_structure.account_list.append(
            self._create_target_info(
                'approval',
                'approval'
            )
        )

    def _target_is_account_id(self):
        response = self.organizations.client.describe_account(
            AccountId=str(self.path)
        ).get('Account')
        if Target._account_is_active(response):
            self.target_structure.account_list.append(
                self._create_target_info(
                    response.get('Name'),
                    str(response.get('Id'))
                )
            )

    def _target_is_ou_id(self):
        responses = self.organizations.get_accounts_for_parent(
            str(self.path)
        )
        for response in responses:
            if Target._account_is_active(response):
                self.target_structure.account_list.append(
                    self._create_target_info(
                        response.get('Name'),
                        str(response.get('Id'))
                    )
                )

    def _target_is_ou_path(self):
        responses = self.organizations.dir_to_ou(self.path)
        for response in responses:
            if Target._account_is_active(response):
                self.target_structure.account_list.append(
                    self._create_target_info(
                        response.get('Name'),
                        str(response.get('Id'))
                    )
                )

    def fetch_accounts_for_target(self):
        if self.path == 'approval':
            return self._target_is_approval()

        if (str(self.path)).startswith('ou-'):
            return self._target_is_ou_id()

        if not (str(self.path).startswith('ou-')
                or str(self.path).startswith('/')):
            return self._target_is_account_id()

        if (str(self.path)).startswith('/'):
            return self._target_is_ou_path()

        raise Exception("Unknown defintion for target")
