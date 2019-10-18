# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for working with Targets within the Deployment Map.
Targets are the stages/steps within a Pipeline and can
require mutation depending on their structure.
"""

import re
import os
from errors import InvalidDeploymentMapError, NoAccountsFoundError

ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]

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
            if target.get('target'):
                target["path"] = target.get('target')
            if not isinstance(target.get('path'), list):
                target["path"] = [target.get('path')]
        if not isinstance(target, list):
            target = [target]
        return target


class Target():
    def __init__(self, path, target_structure, organizations, step, regions):
        self.path = path
        self.step_name = step.get('name', '')
        self.provider = step.get('provider', {})
        self.properties = step.get('properties', {})
        self.regions = [regions] if not isinstance(regions, list) else regions
        self.target_structure = target_structure
        self.organizations = organizations

    @staticmethod
    def _account_is_active(account):
        return bool(account.get('Status') == 'ACTIVE')

    def _create_target_info(self, name, account_id):
        return {
            "id": account_id,
            "name": re.sub(r'[^A-Za-z0-9.@\-_]+', '', name),
            "path": self.path,
            "properties": self.properties,
            "provider": self.provider,
            "regions": self.regions,
            "step_name": re.sub(r'[^A-Za-z0-9.@\-_]+', '', self.step_name)
        }

    def _target_is_approval(self):
        self.target_structure.account_list.append(
            self._create_target_info(
                'approval',
                'approval'
            )
        )

    def _create_response_object(self, responses):
        _entities = 0
        for response in responses:
            _entities += 1
            if Target._account_is_active(response):
                self.target_structure.account_list.append(
                    self._create_target_info(
                        response.get('Name'),
                        str(response.get('Id'))
                    )
                )
        if _entities == 0:
            raise NoAccountsFoundError("No Accounts found in {0}".format(self.path))

    def _target_is_account_id(self):
        responses = self.organizations.client.describe_account(
            AccountId=str(self.path)
        ).get('Account')
        self._create_response_object([responses])

    def _target_is_tags(self):
        responses = self.organizations.get_account_ids_for_tags(self.path)
        self._create_response_object(responses)

    def _target_is_ou_id(self):
        responses = self.organizations.get_accounts_for_parent(
            str(self.path)
        )
        self._create_response_object(responses)

    def _target_is_ou_path(self):
        responses = self.organizations.dir_to_ou(self.path)
        self._create_response_object(responses)

    def _target_is_null_path(self):
        self.path = '/deployment' # TODO we will fetch this from parameter store
        responses = self.organizations.dir_to_ou(self.path)
        self._create_response_object(responses)

    def fetch_accounts_for_target(self):
        if self.path == 'approval':
            return self._target_is_approval()
        if (type(self.path) is dict):
            return self._target_is_tags()
        if (str(self.path)).startswith('ou-'):
            return self._target_is_ou_id()
        if (str(self.path).isnumeric() and len(str(self.path)) == 12):
            return self._target_is_account_id()
        if (str(self.path)).startswith('/'):
            return self._target_is_ou_path()
        if self.path is None:
            return self._target_is_null_path() # No path/target has been passed, path will default to /deployment
        raise InvalidDeploymentMapError("Unknown defintion for target: {0}".format(self.path))
