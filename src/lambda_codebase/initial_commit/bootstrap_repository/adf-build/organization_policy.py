# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy (SCP/Tagging) module used throughout the ADF.
"""

import glob
import ast
import os

from organizations import Organizations
from errors import ParameterNotFoundError
from logger import configure_logger

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")


class OrganizationPolicy:
    def __init__(self):
        pass

    @staticmethod
    def _find_all_paths(policy):
        _files = list(
            glob.iglob(
                f"./adf-bootstrap/**/{policy}*.json",
                recursive=True,
            )
        )
        return [f.replace("./adf-bootstrap", ".") for f in _files]

    def _compare_ordered_policy(self, obj):
        if isinstance(obj, dict):
            return sorted((k, self._compare_ordered_policy(v)) for k, v in obj.items())
        if isinstance(obj, list):  # pylint: disable=R1705
            return sorted(self._compare_ordered_policy(x) for x in obj)
        else:
            return obj

    @staticmethod
    def _trim_policy_file_name(policy):
        # Returns policy target and filename as tuple
        policy_filename = policy.split('/')[-1]
        # `policy` should be formatted "./{target/path/here}/{policy_filename.json}"
        # Target is defined by {target/path/here}
        policy_target = '/'.join(policy.split('/')[1:-1])
        if policy_target == '':
            # if {target/path/here} is empty, target is root
            policy_target = '/'
        return policy_target, policy_filename

    @staticmethod
    def _is_govcloud(region: str) -> bool:
        """
        Evaluates the region to determine if it is part of GovCloud.

        :param region: a region (us-east-1, us-gov-west-1)
        :return: Returns True if the region is GovCloud, False otherwise.
        """
        return region.startswith("us-gov")

    @staticmethod
    def return_policy_name(policy_type, target_path, policy_filename):
        _type = 'scp' if policy_type == "SERVICE_CONTROL_POLICY" else 'tagging-policy'
        if policy_filename != f'{_type}.json':
            #filter the policy name to remove the .json extension
            policy_filename = policy_filename.split('.')[0]
            return f'adf-{_type}-{target_path}-{policy_filename}'
        # Added for backwards-compatibility with previous versions of ADF
        return f'adf-{_type}-{target_path}'

    @staticmethod
    def set_scp_attachment(access_identifier, organization_mapping, path, organizations):
        if access_identifier:
            if access_identifier.get("keep-default-scp") != "enabled":
                try:
                    organizations.detach_policy(
                        "p-FullAWSAccess", organization_mapping[path]
                    )
                except organizations.client.exceptions.PolicyNotAttachedException:
                    LOGGER.info(
                        "FullAWSAccess will stay detached since "
                        "keep-default-scp is not enabled. Path is: %s",
                        path,
                    )
            else:
                try:
                    organizations.attach_policy(
                        "p-FullAWSAccess", organization_mapping[path]
                    )
                except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                    LOGGER.info(
                        "FullAWSAccess will stay attached since "
                        "keep-default-scp is enabled. Path is: %s",
                        path,
                    )

    @staticmethod
    def clean_and_remove_policy_attachment(
        organization_mapping, path, policy_filename, organizations, policy_type
    ):
        policy_name = OrganizationPolicy.return_policy_name(policy_type, path, policy_filename)
        policy_id = organizations.describe_policy_id_for_target(
            organization_mapping[path],
            policy_name,
            policy_type,
        )
        if policy_type == "SERVICE_CONTROL_POLICY":
            try:
                organizations.attach_policy(
                    "p-FullAWSAccess",
                    organization_mapping[path],
                )
            except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                pass
            if policy_id:
                organizations.detach_policy(policy_id, organization_mapping[path])
                organizations.delete_policy(policy_id)
                LOGGER.info('Policy (%s) %s will be deleted. Name is %s',
                            policy_type, organization_mapping[path], policy_name)

    def apply(
        self, organizations, parameter_store, config
    ):
        # pylint: disable=too-many-locals
        status = organizations.get_organization_info()
        if status.get("feature_set") != "ALL":
            LOGGER.info(
                "All Features are currently NOT enabled for this Organization, "
                "this is required to apply SCPs or Tagging Policies",
            )
            return

        LOGGER.info(
            "Determining if Organization Policy changes are required. "
            "(Tagging or Service Controls)",
        )
        organization_mapping = organizations.get_organization_map(
            {
                "/": organizations.get_ou_root_id(),
            }
        )

        supported_policies = ["SERVICE_CONTROL_POLICY", "TAG_POLICY"]

        if self._is_govcloud(REGION_DEFAULT):
            supported_policies = ["SERVICE_CONTROL_POLICY"]

        for policy_type in supported_policies:
            _type = 'scp' if policy_type == "SERVICE_CONTROL_POLICY" else 'tagging-policy'
            organizations.enable_organization_policies(policy_type)
            policy_paths = OrganizationPolicy._find_all_paths(_type)
            LOGGER.info(
                "Policy_paths are %s",
                policy_paths
            )
            try:
                current_stored_policy = ast.literal_eval(
                    parameter_store.fetch_parameter(_type)
                )
                LOGGER.info(
                    "current_stored_policy for type %s is: %s",
                    _type,
                    current_stored_policy,
                )

                for stored_policy in current_stored_policy:
                    path, policy_filename = OrganizationPolicy._trim_policy_file_name(stored_policy)
                    OrganizationPolicy.set_scp_attachment(
                        config.get("scp"), organization_mapping, path, organizations
                    )
                    if stored_policy not in policy_paths:
                        path, policy_filename = OrganizationPolicy._trim_policy_file_name(
                            stored_policy
                        )
                        OrganizationPolicy.clean_and_remove_policy_attachment(
                            organization_mapping,
                            path,
                            policy_filename,
                            organizations,
                            policy_type
                        )
            except ParameterNotFoundError:
                LOGGER.debug(
                    "Parameter %s was not found in Parameter Store, continuing.",
                    _type,
                )

            for policy_path in policy_paths:
                path, policy_filename = OrganizationPolicy._trim_policy_file_name(policy_path)
                policy_name = OrganizationPolicy.return_policy_name(
                    policy_type,
                    path,
                    policy_filename
                )
                policy_id = organizations.describe_policy_id_for_target(
                    organization_mapping[path],
                    policy_name,
                    policy_type
                )
                proposed_policy = Organizations.get_policy_body(policy_path)
                if policy_id:
                    current_policy = organizations.describe_policy(policy_id)
                    if self._compare_ordered_policy(
                        current_policy.get("Content")
                    ) == self._compare_ordered_policy(proposed_policy):
                        LOGGER.info(
                            "Policy (%s) %s does not require updating. Name is: %s",
                            _type,
                            organization_mapping[path],
                            policy_name,
                        )
                        continue
                    LOGGER.info(
                        "Policy (%s) will be updated for %s. Name is: %s",
                        _type,
                        organization_mapping[path],
                        policy_name,
                    )
                    organizations.update_policy(
                        proposed_policy,
                        policy_id,
                    )
                    continue
                try:
                    policy_id = organizations.create_policy(
                        proposed_policy,
                        policy_name,
                        policy_type
                    )
                    LOGGER.info(
                        "Policy (%s) has been created for %s. Name is: %s",
                        _type,
                        organization_mapping[path],
                        policy_name
                    )
                    organizations.attach_policy(
                        policy_id,
                        organization_mapping[path],
                    )
                except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                    LOGGER.info(
                        "Policy (%s) for %s with name %s exists and is attached already.",
                        _type,
                        organization_mapping[path],
                        policy_name
                    )
                except organizations.client.exceptions.DuplicatePolicyException:
                    LOGGER.info(
                        "Policy (%s) for %s with name %s exists ensuring attached.",
                        _type,
                        organization_mapping[path],
                        policy_name
                    )
                    policy_id = organizations.list_policies(
                        policy_name,
                        _type
                    )
                    organizations.attach_policy(policy_id, organization_mapping[path])
            parameter_store.put_parameter(_type, str(policy_paths))
