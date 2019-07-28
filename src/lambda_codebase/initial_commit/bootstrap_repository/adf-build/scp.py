# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""SCP module used throughout the ADF
"""

import glob
import ast
from organizations import Organizations
from errors import ParameterNotFoundError
from logger import configure_logger

LOGGER = configure_logger(__name__)

class SCP:
    def __init__(self):
        pass

    @staticmethod
    def _find_all():
        return [scp for scp in glob.iglob('./**/scp.json', recursive=True)]

    def _compare_ordered_policy(self, obj):
        if isinstance(obj, dict):
            return sorted((k, self._compare_ordered_policy(v)) for k, v in obj.items())
        if isinstance(obj, list): #pylint: disable=R1705
            return sorted(self._compare_ordered_policy(x) for x in obj)
        else:
            return obj

    @staticmethod
    def _trim_scp_file_name(scp):
        return scp[1:][:-8] if scp[1:][:-8] == '/' else scp[2:][:-9]

    def apply(self, organizations, parameter_store, config): #pylint: disable=R0912, R0915
        status = organizations.get_organization_info()

        if status.get('feature_set') != 'ALL':
            LOGGER.info('All Features are currently NOT enabled for this Organization, this is required to apply SCPs')
            return

        organizations.enable_scp()
        scps = SCP._find_all()

        LOGGER.info('Determining if SCP changes are required')
        organization_mapping = organizations.get_organization_map({'/': organizations.get_ou_root_id()})
        scp_keep_full_access = config.get('scp')
        try:
            current_stored_scps = ast.literal_eval(
                parameter_store.fetch_parameter('scp')
            )
            for stored_scp in current_stored_scps:
                path = SCP._trim_scp_file_name(stored_scp)
                if scp_keep_full_access:
                    if scp_keep_full_access.get('keep-default-scp') != 'enabled':
                        try:
                            organizations.detach_scp('p-FullAWSAccess', organization_mapping[path])
                        except organizations.client.exceptions.PolicyNotAttachedException:
                            LOGGER.info('FullAWSAccess will stay detached since keep-default-scp is not enabled. Path is: %s', path)
                    else:
                        try:
                            organizations.attach_scp('p-FullAWSAccess', organization_mapping[path])
                        except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                            LOGGER.info('FullAWSAccess will stay attached since keep-default-scp is enabled. Path is: %s', path)
                            pass
                if stored_scp not in scps:
                    scp_id = organizations.describe_scp_id_for_target(organization_mapping[path])
                    try:
                        organizations.attach_scp('p-FullAWSAccess', organization_mapping[path])
                    except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                        pass
                    organizations.detach_scp(scp_id, organization_mapping[path])
                    organizations.delete_scp(scp_id)
                    LOGGER.info('SCP %s will be deleted. Path is: %s', organization_mapping[path], path)
        except ParameterNotFoundError:
            LOGGER.debug('Parameter "scp" was not found in Parameter Store, continuing.')
            pass

        for scp in scps:
            path = SCP._trim_scp_file_name(scp)
            scp_id = organizations.describe_scp_id_for_target(organization_mapping[path])
            proposed_scp = Organizations.get_scp_body(scp)
            if scp_id:
                current_scp = organizations.describe_scp(scp_id)
                if self._compare_ordered_policy(current_scp.get('Content')) == self._compare_ordered_policy(proposed_scp):
                    LOGGER.info('SCP %s does not require updating. Path is: %s', organization_mapping[path], path)
                    continue
                LOGGER.info('SCP will be updated for %s. Path is: %s', organization_mapping[path], path)
                organizations.update_scp(
                    proposed_scp,
                    scp_id
                )
                continue
            try:
                policy_id = organizations.create_scp(
                    proposed_scp,
                    path
                )
                LOGGER.info('SCP has been created for %s. Path is: %s', organization_mapping[path], path)
                organizations.attach_scp(policy_id, organization_mapping[path])
            except organizations.client.exceptions.DuplicatePolicyException:
                LOGGER.info('SCP for %s already exists but was not attached, attaching.', organization_mapping[path])
                policy_id = organizations.list_scps('adf-scp-{0}'.format(path))
                organizations.attach_scp(policy_id, organization_mapping[path])

        parameter_store.put_parameter('scp', str(scps))
