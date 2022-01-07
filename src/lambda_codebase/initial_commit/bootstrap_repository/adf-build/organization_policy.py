# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Organizations Policy (SCP/Tagging) module used throughout the ADF
"""

import glob
import ast
import os

from organizations import Organizations
from errors import ParameterNotFoundError
from logger import configure_logger

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv('AWS_REGION')


class OrganizationPolicy:
    def __init__(self):
        pass

    @staticmethod
    def _find_all(policy):
        _files = list(glob.iglob(
            f'./adf-bootstrap/**/{policy}.json',
            recursive=True,
        ))
        return [f.replace('./adf-bootstrap', '.') for f in _files]

    def _compare_ordered_policy(self, obj):
        if isinstance(obj, dict):
            return sorted((k, self._compare_ordered_policy(v))
                          for k, v in obj.items())
        if isinstance(obj, list):  # pylint: disable=R1705
            return sorted(self._compare_ordered_policy(x) for x in obj)
        else:
            return obj

    @staticmethod
    def _trim_scp_file_name(policy):
        return policy[1:][:-8] if policy[1:][:-8] == '/' else policy[2:][:-9]

    @staticmethod
    def _trim_tagging_policy_file_name(policy):
        return policy[1:][:-19] if policy[1:][:-19] == '/' else policy[2:][:-20]

    @staticmethod
    def _is_govcloud(region: str) -> bool:
        """Evaluates the region to determine if it is part of GovCloud.

        :param region: a region (us-east-1, us-gov-west-1)
        :return: Returns True if the region is GovCloud, False otherwise.
        """
        return region.startswith('us-gov')

    @staticmethod
    def set_scp_attachment(
            access_identifer,
            organization_mapping,
            path,
            organizations):
        if access_identifer:
            if access_identifer.get('keep-default-scp') != 'enabled':
                try:
                    organizations.detach_policy(
                        'p-FullAWSAccess', organization_mapping[path])
                except organizations.client.exceptions.PolicyNotAttachedException:
                    LOGGER.info(
                        'FullAWSAccess will stay detached since keep-default-scp is not enabled. Path is: %s',
                        path)
            else:
                try:
                    organizations.attach_policy(
                        'p-FullAWSAccess', organization_mapping[path])
                except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                    LOGGER.info(
                        'FullAWSAccess will stay attached since keep-default-scp is enabled. Path is: %s',
                        path)
                    pass

    @staticmethod
    def clean_and_remove_policy_attachment(
            organization_mapping,
            path,
            organizations,
            policy_type):
        policy_id = organizations.describe_policy_id_for_target(
            organization_mapping[path], policy_type)
        if policy_type == 'SERVICE_CONTROL_POLICY':
            try:
                organizations.attach_policy(
                    'p-FullAWSAccess', organization_mapping[path])
            except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                pass
        organizations.detach_policy(policy_id, organization_mapping[path])
        organizations.delete_policy(policy_id)
        LOGGER.info('Policy (%s) %s will be deleted. Path is: %s',
                    policy_type, organization_mapping[path], path)

    def apply(self, organizations, parameter_store, config):  # pylint: disable=R0912, R0915
        status = organizations.get_organization_info()
        if status.get('feature_set') != 'ALL':
            LOGGER.info(
                'All Features are currently NOT enabled for this Organization, this is required to apply SCPs or Tagging Policies')
            return

        LOGGER.info(
            'Determining if Organization Policy changes are required. (Tagging or Service Controls)')
        organization_mapping = organizations.get_organization_map(
            {'/': organizations.get_ou_root_id()})

        supported_policies = [
            'scp',
            'tagging-policy'
        ]

        if self._is_govcloud(REGION_DEFAULT):
            supported_policies = ['scp']

        for policy in supported_policies:
            _type = 'SERVICE_CONTROL_POLICY' if policy == 'scp' else 'TAG_POLICY'
            organizations.enable_organization_policies(_type)
            _policies = OrganizationPolicy._find_all(policy)
            try:
                current_stored_policy = ast.literal_eval(
                    parameter_store.fetch_parameter(policy)
                )
                for stored_policy in current_stored_policy:
                    path = OrganizationPolicy._trim_scp_file_name(
                        stored_policy) if policy == 'scp' else OrganizationPolicy._trim_tagging_policy_file_name(stored_policy)
                    OrganizationPolicy.set_scp_attachment(
                        config.get('scp'),
                        organization_mapping,
                        path,
                        organizations
                    )
                    if stored_policy not in _policies:
                        OrganizationPolicy.clean_and_remove_policy_attachment(
                            organization_mapping, path, organizations, _type)
            except ParameterNotFoundError:
                LOGGER.debug(
                    'Parameter %s was not found in Parameter Store, continuing.', policy)
                pass

            for _policy in _policies:
                path = OrganizationPolicy._trim_scp_file_name(
                    _policy) if policy == 'scp' else OrganizationPolicy._trim_tagging_policy_file_name(_policy)
                policy_id = organizations.describe_policy_id_for_target(
                    organization_mapping[path], _type)
                proposed_policy = Organizations.get_policy_body(_policy)
                if policy_id:
                    current_policy = organizations.describe_policy(policy_id)
                    if self._compare_ordered_policy(current_policy.get(
                            'Content')) == self._compare_ordered_policy(proposed_policy):
                        LOGGER.info(
                            'Policy (%s) %s does not require updating. Path is: %s',
                            policy,
                            organization_mapping[path],
                            path)
                        continue
                    LOGGER.info(
                        'Policy (%s) will be updated for %s. Path is: %s',
                        policy,
                        organization_mapping[path],
                        path)
                    organizations.update_policy(
                        proposed_policy,
                        policy_id
                    )
                    continue
                try:
                    policy_id = organizations.create_policy(
                        proposed_policy,
                        path,
                        _type
                    )
                    LOGGER.info(
                        'Policy (%s) has been created for %s. Path is: %s',
                        policy,
                        organization_mapping[path],
                        path)
                    organizations.attach_policy(
                        policy_id, organization_mapping[path])
                except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                    LOGGER.info(
                        'Policy (%s) for %s exists and is attached already.',
                        policy,
                        organization_mapping[path])
                except organizations.client.exceptions.DuplicatePolicyException:
                    LOGGER.info(
                        'Policy (%s) for %s exists ensuring attached.',
                        policy,
                        organization_mapping[path])
                    policy_id = organizations.list_policies(
                        f'adf-{policy}-{path}', _type)
                    organizations.attach_policy(
                        policy_id, organization_mapping[path])
            parameter_store.put_parameter(policy, str(_policies))
