# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy module used throughout the ADF.
"""

import glob
import os
import os
import json
import boto3

from logger import configure_logger
from typing import List
from organisation_policy_campaign import (
    OrganizationPolicyTarget,
    OrganizationalPolicyCampaignPolicy,
    OrganizationPolicyApplicationCampaign,
)

from organizations import Organizations

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")
ENABLE_V2 = os.getenv("ENABLE_V2", True)


class OrganizationPolicy:
    def __init__(self):
        pass

    @staticmethod
    def _find_all(policy):
        _files = list(
            glob.iglob(
                f"./adf-bootstrap/**/{policy}.json",
                recursive=True,
            )
        )
        return [f.replace("./adf-bootstrap", ".") for f in _files]

    @staticmethod
    def _find_all_polices_v2(policy):
        _files = list(
            glob.iglob(
                f"./adf-bootstrap/{policy}/*.json",
                recursive=True,
            )
        )
        return [f.replace("./adf-bootstrap", ".") for f in _files]

    @staticmethod
    def _compare_ordered_policy(obj):
        LOGGER.info(obj)
        if isinstance(obj, dict):
            return sorted(
                (k, OrganizationPolicy._compare_ordered_policy(v))
                for k, v in obj.items()
            )
        if isinstance(obj, list):  # pylint: disable=R1705
            return sorted(OrganizationPolicy._compare_ordered_policy(x) for x in obj)
        else:
            return obj

    @staticmethod
    def _trim_scp_file_name(policy):
        return policy[1:][:-8] if policy[1:][:-8] == "/" else policy[2:][:-9]

    @staticmethod
    def _trim_tagging_policy_file_name(policy):
        return policy[1:][:-19] if policy[1:][:-19] == "/" else policy[2:][:-20]

    @staticmethod
    def _is_govcloud(region: str) -> bool:
        """
        Evaluates the region to determine if it is part of GovCloud.

        :param region: a region (us-east-1, us-gov-west-1)
        :return: Returns True if the region is GovCloud, False otherwise.
        """
        return region.startswith("us-gov")

    @staticmethod
    def set_scp_attachment(access_identifer, organization_mapping, path, organizations):
        if access_identifer:
            if access_identifer.get("keep-default-scp") != "enabled":
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
        organization_mapping, path, organizations, policy_type
    ):
        policy_id = organizations.describe_policy_id_for_target(
            organization_mapping[path],
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
        organizations.detach_policy(policy_id, organization_mapping[path])
        organizations.delete_policy(policy_id)
        LOGGER.info(
            "Policy (%s) %s will be deleted. Path is: %s",
            policy_type,
            organization_mapping[path],
            path,
        )

    def apply(
        self, organizations, parameter_store, config
    ):  # pylint: disable=R0912, R0915
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
        LOGGER.info("Building organization map")
        organization_mapping = organizations.get_organization_map(
            {
                "/": organizations.get_ou_root_id(),
            }
        )
        LOGGER.info("Organization map built")

        supported_policies = {
            "scp": "SERVICE_CONTROL_POLICY",
            "tagging-policy": "TAG_POLICY",
        }

        if self._is_govcloud(REGION_DEFAULT):
            supported_policies = {
                "scp": "SERVICE_CONTROL_POLICY",
            }

        self.apply_policies(
            organizations,
            parameter_store,
            config,
            organization_mapping,
            supported_policies,
        )

    def apply_policies(
        self,
        organizations,
        parameter_store,
        config,
        organization_mapping,
        supported_policies,
    ):
        LOGGER.info("V2 Method for applying policies")
        for policy, policy_type in supported_policies.items():
            _type = policy_type
            campaign = OrganizationPolicyApplicationCampaign(
                _type,
                organization_mapping,
                config.get("scp"),
                boto3.client("organizations"),
            )
            organizations.enable_organization_policies(_type)

            _legacy_policies = OrganizationPolicy._find_all(policy)
            LOGGER.info(
                "Discovered the following legacy policies: %s", _legacy_policies
            )
            for _policy in _legacy_policies:
                LOGGER.info("Loading policy: %s", _policy)
                proposed_policy = json.loads(Organizations.get_policy_body(_policy))

                path = (
                    OrganizationPolicy._trim_scp_file_name(_policy)
                    if policy == "scp"
                    else OrganizationPolicy._trim_tagging_policy_file_name(_policy)
                )
                proposed_policy_name = f"adf-{policy}-{path}"
                LOGGER.info(proposed_policy)
                policy_instance = campaign.get_policy(
                    proposed_policy_name, proposed_policy
                )
                target = campaign.get_target(path)
                policy_instance.set_targets([target])

                LOGGER.info(target)

            _policies = OrganizationPolicy._find_all_polices_v2(policy)
            LOGGER.info("Discovered the following policies: %s", _policies)
            for _policy in _policies:
                policy_definition = json.loads(Organizations.get_policy_body(_policy))
                # TODO: Schema validation here
                LOGGER.info(policy_definition)
                proposed_policy = policy_definition.get("Policy")
                proposed_policy_name = policy_definition.get("PolicyName")
                policy = campaign.get_policy(proposed_policy_name, proposed_policy)
                targets = policy_definition.get("Targets", [])

                LOGGER.info(organization_mapping)
                policy.set_targets([campaign.get_target(t) for t in targets])
            campaign.apply()
            # parameter_store.put_parameter(policy, str(_policies))
