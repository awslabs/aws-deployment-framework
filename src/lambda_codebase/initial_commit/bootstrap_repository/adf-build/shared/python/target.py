# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Module used for working with Targets within the Deployment Map.
Targets are the stages/steps within a Pipeline and can
require mutation depending on their structure.
"""

import re
import os

import boto3

# ADF imports
from errors import (
    InvalidDeploymentMapError,
    NoAccountsFoundError,
    InsufficientWaveSizeError,
)
from botocore.exceptions import ClientError
from logger import configure_logger
from parameter_store import ParameterStore
from schema_validation import AWS_ACCOUNT_ID_REGEX_STR

LOGGER = configure_logger(__name__)
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]

AWS_ACCOUNT_ID_REGEX = re.compile(AWS_ACCOUNT_ID_REGEX_STR)
CLOUDFORMATION_PROVIDER_NAME = "cloudformation"
RECURSIVE_SUFFIX = "/**/*"


class TargetStructure:
    def __init__(self, target):
        self.target = TargetStructure._define_target_type(target)
        self.account_list = []
        self.wave = (
            target.get('wave', {})
            if isinstance(target, dict)
            else {}
        )
        self.exclude = (
            target.get('exclude', [])
            if isinstance(target, dict)
            else []
        )

    @staticmethod
    def _define_target_type(target) -> list[dict]:
        if isinstance(target, list):
            output = []
            for target_path in target:
                output.append({"path": [target_path]})
            target = output
        if isinstance(target, (int, str)):
            target = [{"path": [target]}]
        if isinstance(target, dict):
            if target.get('target'):
                target["path"] = target.get('target')
            if not target.get('path') and not target.get('tags'):
                target["path"] = '/deployment'
                LOGGER.debug(
                    'No path/target detected, defaulting to /deployment',
                )
            if not isinstance(target.get('path', []), list):
                target["path"] = [target.get('path')]
        if not isinstance(target, list):
            target = [target]
        return target

    @staticmethod
    def _get_actions_per_target_account(
        regions: list,
        provider: str,
        action: str,
        change_set_approval: bool,
    ) -> int:
        """Given a List of target regions, the provider, action type and wether
        change_set_approval has been set
        return the calculated number of actions which will be generated per
        target_account"""
        regions_defined = len(regions)
        actions_per_region = 1
        if provider == CLOUDFORMATION_PROVIDER_NAME and not action:
            # add 1 or 2 actions for changesets with approvals
            actions_per_region += (1 + int(change_set_approval))
        return actions_per_region * regions_defined

    def generate_waves(self, target):
        """ Given the maximum actions allowed in a wave via wave.size property,
        reduce the accounts allocated in each wave by a factor
        matching the number of actions necessary per account, which inturn
        derived from the number of target regions and the specific action_type
        defined for that target. """
        wave_size = self.wave.get('size', 50)
        actions_per_target_account = self._get_actions_per_target_account(
            regions=target.regions,
            provider=target.provider,
            action=target.properties.get("action"),
            change_set_approval=target.properties.get("change_set_approval", False),
        )

        if actions_per_target_account > wave_size:
            # Left of scope:
            # Theoretically the region deployment actions could be split
            # across different waves but that requires a whole bunch more
            # refactoring as waves are representing accounts not actions today
            raise InsufficientWaveSizeError(
                f"Wave size : {wave_size} set, however: "
                f"{actions_per_target_account} actions necessary per target"
            )
        # Reduce the wave size by the number of actions per target
        wave_size = wave_size // actions_per_target_account
        waves = []
        length = len(self.account_list)

        for start_index in range(0, length, wave_size):
            end_index = min(
                start_index + wave_size,
                length,
            )
            waves.append(
                self.account_list[start_index:end_index],
            )
        return waves

class Target:
    """
    Target deployment configuration.
    """
    def __init__(
        self,
        path,
        target_structure,
        organizations,
        step,
    ):
        self.path = path
        self.step_name = step.get('name', '')
        self.provider = step.get('provider', 'cloudformation')
        self.properties = step.get('properties', {})
        self.regions = (
            [step.get('regions')]
            if not isinstance(step.get('regions'), list)
            else step.get('regions')
        )
        self.target_structure = target_structure
        self.organizations = organizations
        # Set adf_deployment_maps_allow_empty_target as bool
        parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
        self.adf_deployment_maps_allow_empty_target = (
            parameter_store.fetch_parameter(
                "deployment_maps/allow_empty_target"
            ).lower() == "enabled"
        )

    @staticmethod
    def _account_is_active(account):
        return bool(account.get("Status") == "ACTIVE")

    def _create_target_info(self, name, account_id):
        return {
            "id": account_id,
            "name": re.sub(r"[^A-Za-z0-9.@\-_]+", "", name),
            "path": self.path,
            "properties": self.properties,
            "provider": self.provider,
            "regions": self.regions,
            "step_name": re.sub(r"[^A-Za-z0-9.@\-_]+", "", self.step_name),
        }

    def _target_is_approval(self):
        self.target_structure.account_list.append(
            self._create_target_info("approval", "approval")
        )

    def _create_response_object(self, responses):
        accounts_found = 0
        for response in responses:
            is_active_not_excluded = (
                Target._account_is_active(response)
                and not response.get('Id') in self.target_structure.exclude
            )
            if is_active_not_excluded:
                accounts_found += 1
                self.target_structure.account_list.append(
                    self._create_target_info(
                        response.get("Name"), str(response.get("Id"))
                    )
                )

        if accounts_found == 0:
            if not self.adf_deployment_maps_allow_empty_target:
                raise NoAccountsFoundError(f"No accounts found in {self.path}.")
            LOGGER.info(
                "Create_response_object: 0 AWS accounts found for path %s. "
                "Continue with empty response.",
                self.path,
            )

    def _target_is_account_id(self):
        try:
            responses = self.organizations.client.describe_account(
                AccountId=str(self.path)
            ).get('Account')
            responses_list = [responses]
        except ClientError as client_err:
            if (
                client_err.response["Error"]["Code"] == "AccountNotFoundException" and
                self.adf_deployment_maps_allow_empty_target
            ):
                LOGGER.info("IGNORE - Account was not found in AWS Org for id %s", self.path)
                responses_list = []
            else:
                raise
        self._create_response_object(responses_list)

    def _target_is_tags(self):
        responses = self.organizations.get_account_ids_for_tags(self.path)
        accounts = []
        for response in responses:
            if response.startswith('ou-'):
                accounts.extend(
                    self.organizations.get_accounts_for_parent(response),
                )
            else:
                accounts.append(
                    self.organizations.client
                    .describe_account(AccountId=response)
                    .get('Account'),
                )
        self._create_response_object(accounts)

    def _target_is_ou_id(self):
        try:
            # Check if ou exists - otherwise throw clean exception here
            self.organizations.client.list_children(ParentId=self.path, ChildType="ACCOUNT")
            responses = self.organizations.get_accounts_for_parent(
                str(self.path)
            )
        except ClientError as client_err:
            no_target_found = (
                client_err.response["Error"]["Code"] == "ParentNotFoundException"
            )
            if no_target_found and self.adf_deployment_maps_allow_empty_target:
                LOGGER.info(
                    "Note: Target OU was not found in the AWS Org for id %s",
                    self.path,
                )
                responses = []
            else:
                raise
        self._create_response_object(responses)

    def _target_is_ou_path(self, resolve_children=False):
        try:
            responses = self.organizations.get_accounts_in_path(
                self.path,
                resolve_children=resolve_children,
                ou_id=None,
                excluded_paths=[],
            )
        except Exception:
            if self.adf_deployment_maps_allow_empty_target:
                LOGGER.info(
                    "Note: Target OU was not found in AWS Org for path %s",
                    self.path,
                )
                responses = []
            else:
                raise
        self._create_response_object(responses)

    def _target_is_null_path(self):
        # TODO we need to fetch this default path from parameter store
        self.path = '/deployment'
        responses = self.organizations.dir_to_ou(self.path)
        self._create_response_object(responses)

    # pylint: disable=R0911
    def fetch_accounts_for_target(self):
        if self.path == "approval":
            self._target_is_approval()
            return
        if isinstance(self.path, dict):
            self._target_is_tags()
            return
        if str(self.path).startswith("ou-"):
            self._target_is_ou_id()
            return
        if AWS_ACCOUNT_ID_REGEX.match(str(self.path)):
            self._target_is_account_id()
            return
        if str(self.path).isnumeric():
            LOGGER.warning(
                "The specified path is numeric, but is not 12 chars long. "
                "This typically happens when you specify the account id as a "
                "number, while the account id starts with a zero. If this is "
                "the case, please wrap the account id in quotes to make it a "
                "string. The current path is interpreted as '%s'. "
                "It could be interpreted as an octal number due to the zero, "
                "so it might not match the account id as specified in the "
                "deployment map. Interpreted as an octal it would be '%s'. "
                "This error is thrown to be on the safe side such that it "
                "is not targeting the wrong account by accident.",
                str(self.path),
                # Optimistically convert the path from 10-base to octal 8-base
                # Then remove the use of the 'o' char, as it will output
                # in the correct way, starting with: 0o.
                str(oct(int(self.path))).replace("o", ""),
            )
        if str(self.path).startswith("/"):
            self._target_is_ou_path(
                resolve_children=str(self.path).endswith(RECURSIVE_SUFFIX)
            )
            return

        if self.adf_deployment_maps_allow_empty_target:
            return

        if self.path is None:
            # No path/target has been passed, path will default to /deployment
            self._target_is_null_path()
            return
        raise InvalidDeploymentMapError(f"Unknown definition for target: {self.path}")
