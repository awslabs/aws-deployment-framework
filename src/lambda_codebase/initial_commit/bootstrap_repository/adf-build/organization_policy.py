# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Organizations Policy (SCP/Tagging) module used throughout the ADF
"""

import glob
import ast
from organizations import Organizations
from errors import ParameterNotFoundError
from logger import configure_logger

LOGGER = configure_logger(__name__)


class OrganizationPolicy:
    def __init__(self):
        pass

    @staticmethod
    def _find_all_paths(policy):
        # This function returns relative paths (relative to the adf-bootstrap/ directory)
        # of all JSON files that describe policies of type `policy`
        # (e.g. scp, tagging-policy)
        _files = list(glob.iglob(
            './adf-bootstrap/**/{0}*.json'.format(policy),
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
    def _trim_policy_file_name(policy):
        # Returns policy target and filename as tuple
        policy_filename = policy.split('/')[-1]
        # `policy` should be formatted "./{target/path/here}/{policy_filename.json}"
        if '/'.join(policy.split('/')[1:-1]) == '':
            # if {target/path/here} is empty, target is root
            policy_target = '/'
        else:
            # otherwise, target is defined by {target/path/here}
            policy_target = '/'.join(policy.split('/')[1:-1])
        return policy_target, policy_filename

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
    def return_policy_name(policy_type, target_path, policy_filename):
        _type = 'scp' if policy_type == "SERVICE_CONTROL_POLICY" else 'tagging-policy'
        if policy_filename != '{}.json':
            return 'adf-{0}-{1}--{2}'.format(_type, target_path, policy_filename)
        else:
            # Added for backwards-compatibility with previous versions of ADF
            return 'adf-{0}-{1}'.format(_type, target_path)

    @staticmethod
    def clean_and_remove_policy_attachment(
            organization_mapping,
            path,
            policy_filename,
            organizations,
            policy_type):
        policy_name = return_policy_name(policy_type, path, policy_filename)
        policy_id = organizations.describe_policy_id_for_target(
            organization_mapping[path], policy_name, policy_type)
        if policy_type == 'SERVICE_CONTROL_POLICY':
            try:
                organizations.attach_policy(
                    'p-FullAWSAccess', organization_mapping[path])
            except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                pass
        organizations.detach_policy(policy_id, organization_mapping[path])
        organizations.delete_policy(policy_id)
        LOGGER.info('Policy (%s) %s will be deleted. Name is %s',
                    policy_type, organization_mapping[path], policy_name)

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
        for policy_type in ['SERVICE_CONTROL_POLICY', 'TAG_POLICY']:
            _type = 'scp' if policy_type == "SERVICE_CONTROL_POLICY" else 'tagging-policy'
            organizations.enable_organization_policies(policy_type)
            policy_paths = OrganizationPolicy._find_all_paths(_type)
            try:
                current_stored_policy = ast.literal_eval(
                    parameter_store.fetch_parameter(_type)
                )
                for stored_policy in current_stored_policy:
                    path, policy_filename = OrganizationPolicy._trim_policy_file_name(
                        stored_policy)
                    OrganizationPolicy.set_scp_attachment(
                        config.get('scp'),
                        organization_mapping,
                        path,
                        organizations
                    )
                    if stored_policy not in policy_paths:
                        OrganizationPolicy.clean_and_remove_policy_attachment(
                            organization_mapping, path, policy_filename, organizations, _type)
            except ParameterNotFoundError:
                LOGGER.debug(
                    'Parameter %s was not found in Parameter Store, continuing.', _type)
                pass

            for policy_path in policy_paths:
                path, policy_filename = OrganizationPolicy._trim_policy_file_name(
                    policy_path)
                policy_name = return_policy_name(policy_type, path, policy_filename)
                policy_id = organizations.describe_policy_id_for_target(
                    organization_mapping[path], policy_name, _type)
                proposed_policy = Organizations.get_policy_body(policy_path)
                if policy_id:
                    current_policy = organizations.describe_policy(policy_id)
                    if self._compare_ordered_policy(current_policy.get(
                            'Content')) == self._compare_ordered_policy(proposed_policy):
                        LOGGER.info(
                            'Policy (%s) %s does not require updating. Name is %s',
                            _type,
                            organization_mapping[path],
                            policy_name)
                        continue
                    LOGGER.info(
                        'Policy (%s) will be updated for %s. Name is: %s',
                        _type,
                        organization_mapping[path],
                        policy_name)
                    organizations.update_policy(
                        proposed_policy,
                        policy_id
                    )
                    continue
                try:
                    policy_id = organizations.create_policy(
                        proposed_policy,
                        path,
                        policy_name,
                        policy_type
                    )
                    LOGGER.info(
                        'Policy (%s) has been created for %s. Name is: %s',
                        _type,
                        organization_mapping[path],
                        policy_name)
                    organizations.attach_policy(
                        policy_id, organization_mapping[path])
                except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                    LOGGER.info(
                        'Policy (%s) for %s with name %s exists and is attached already.',
                        _type,
                        organization_mapping[path],
                        policy_name)
                except organizations.client.exceptions.DuplicatePolicyException:
                    LOGGER.info(
                        'Policy (%s) for %s with name %s exists ensuring attached.',
                        _type,
                        organization_mapping[path],
                        policy_name)
                    policy_id = organizations.list_policies(
                        policy_name, _type)
                    organizations.attach_policy(
                        policy_id, organization_mapping[path])
            parameter_store.put_parameter(_type, str(policy_paths))
