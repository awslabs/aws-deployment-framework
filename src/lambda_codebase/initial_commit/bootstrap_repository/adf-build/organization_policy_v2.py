# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy (SCP/Tagging) module used throughout the ADF.
"""

import glob
import ast
import os
import json
import string
import boto3

from organizations import Organizations
from errors import ParameterNotFoundError
from logger import configure_logger
from typing import List

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")
ENABLE_V2 = os.getenv("ENABLE_V2", True)


class OrganizationPolicyTarget:
    existing_policy_ids: dict()
    path: string
    type: string
    id: string
    polices_to_be_updated: dict()
    polices_to_be_created: dict()

    def __init__(self, target_path, type, id, organizations_client=None) -> None:

        self.path = target_path
        self.type = type
        self.id = id
        self.polices_to_be_updated = {}
        self.polices_to_be_created = {}
        self.organizations_client = (
            organizations_client
            if organizations_client
            else boto3.client("organizations")
        )
        self.existing_policy_ids = self.get_existing_policies()

    def get_existing_policies(self):
        existing_policy_ids = {
            p["Name"]: p["Id"]
            for p in self.organizations_client.list_policies_for_target(
                TargetId=self.id, Filter=self.type
            ).get("Policies")
            if f"ADF Managed {self.type}" in p.get("Description")
        }
        return existing_policy_ids

    def update_policy(self, policy_id, policy_content):
        policy_already_updated_in_campaign = self.polices_to_be_updated.get(
            policy_id, False
        )
        if not policy_already_updated_in_campaign:
            self.polices_to_be_updated[policy_id] = policy_content
        else:
            raise Exception(
                f"Policy {policy_id} already updated in the campaign for target {self.id}"
            )

    def create_policy(self, policy_name, policy_content):
        policy_created_in_campaign = self.polices_to_be_created.get(policy_name, False)
        if not policy_created_in_campaign:
            self.polices_to_be_updated[policy_name] = policy_content
        else:
            raise Exception(
                f"Policy {policy_name} already created in the campaign for target {self.id}"
            )


class OrganizationalPolicyCampaignPolicy:
    name: string
    body: string
    id: string
    type: string
    current_targets = list()
    targets_requiring_attachment = {}

    def __init__(self, policy_name, policy_body, type, id=None, organizations_client=None):
        self.name = policy_name
        self.body = policy_body
        self.id = id
        self.type = type
        self.organizations_client = (
            organizations_client
            if organizations_client
            else boto3.client("organizations")
        )
        self.current_targets = self.get_current_targets_for_policy()

    def get_current_targets_for_policy(self):
        if self.id:
            current_targets = self.organizations_client.list_targets_for_policy(
                PolicyId=self.id
            ).get("Targets")
            return current_targets
        else:
            return []

    def set_targets(self, targets):
        target: OrganizationPolicyTarget
        for target in targets:
            if target.id in self.current_targets:
                continue
            else:
                self.targets_requiring_attachment[target.id] = target

    def attach_targets(self):
        LOGGER.info("Attaching the policy (%s) to the following targets: %s", self.name, self.targets_requiring_attachment)
        for id in self.targets_requiring_attachment:
            self.organizations_client.attach_policy(
                PolicyId=self.id, TargetId=id
            )

    def create(self):
        policy_type_name = (
            "scp" if self.type == "SERVICE_CONTROL_POLICY" else "tagging-policy"
        )
        response = self.organizations_client.create_policy(Content=json.dumps(self.body),
         Description=f"ADF Managed {policy_type_name}",
         Name=self.name,
         Type=self.type)

        self.id = response.get("Policy").get("PolicySummary").get("Id")
        LOGGER.info("Policy %s created with id: %s", self.name, self.id)
        self.attach_targets()



    def update(self):
        pass

    def delete(self):
        pass



class OrganizationPolicyApplicationCampaign:
    targets: dict()
    type: str
    organizational_mapping: dict
    policies_to_be_created: List[OrganizationalPolicyCampaignPolicy]
    policies_to_be_updated: List[OrganizationalPolicyCampaignPolicy]

    def __init__(self, type, organizational_mapping, organisations_client) -> None:
        self.targets = {}
        self.type = type
        self.organizational_mapping = organizational_mapping
        self.organizations = organisations_client
        self.policies_to_be_created = []
        self.policies_to_be_updated = []
        self.existing_policy_lookup = self.get_existing_policys()

    def get_existing_policys(self):
        response = self.organizations.list_policies(Filter=self.type)
        policy_type_name = (
            "scp" if self.type == "SERVICE_CONTROL_POLICY" else "tagging-policy"
        )
        return {
            p["Name"]: p["Id"]
            for p in response["Policies"]
            if f"ADF Managed {policy_type_name}" in p["Description"]
        }

    def get_target(self, target: str) -> OrganizationPolicyTarget:
        if target not in self.targets:
            self.targets[target] = OrganizationPolicyTarget(
                target_path=target,
                type=self.type,
                id=self.organizational_mapping[target],
                organizations_client=self.organizations,
            )
        return self.targets[target]

    def get_policy(self, policy_name, policy_body):
        if policy_name not in self.existing_policy_lookup:
            return self.create_policy(policy_name, policy_body)
        return self.update_policy(policy_name, policy_body)


    def create_policy(self, policy_name, policy_body):
        policy = OrganizationalPolicyCampaignPolicy(policy_name, policy_body, self.type, None, self.organizations)
        self.policies_to_be_created.append(policy)
        return policy

    def update_policy(self, policy_name, policy_body):
        policy = OrganizationalPolicyCampaignPolicy(
            policy_name, policy_body, self.type, self.existing_policy_lookup[policy_name], self.organizations
        )
        current_policy = self.organizations.describe_policy(self.existing_policy_lookup[policy_name])
        if OrganizationPolicy._compare_ordered_policy(
            current_policy.get("Content")
        ) == OrganizationPolicy._compare_ordered_policy(policy_body):
            return policy
        else:
            self.policies_to_be_created.append(policy)
        return policy

    def apply(self):
        LOGGER.info("The following policies need to be created: %s",
         [policy.name for policy in self.policies_to_be_created])
        for policy in self.policies_to_be_created:
            policy.create()
        LOGGER.info("The following policies need to be updated: %s",
         [policy.name for policy in self.policies_to_be_updated])





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

    def _compare_ordered_policy(self, obj):
        if isinstance(obj, dict):
            return sorted((k, self._compare_ordered_policy(v)) for k, v in obj.items())
        if isinstance(obj, list):  # pylint: disable=R1705
            return sorted(self._compare_ordered_policy(x) for x in obj)
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
        organization_mapping = organizations.get_organization_map(
            {
                "/": organizations.get_ou_root_id(),
            }
        )

        supported_policies = ["scp", "tagging-policy"]

        if self._is_govcloud(REGION_DEFAULT):
            supported_policies = ["scp"]

        if ENABLE_V2:
            self.apply_policies_v2(
                organizations,
                parameter_store,
                config,
                organization_mapping,
                supported_policies,
            )

    def apply_policies_v2(
        self,
        organizations,
        parameter_store,
        config,
        organization_mapping,
        supported_policies,
    ):
        LOGGER.info("V2 Method for applying policies")
        for policy in supported_policies:

            _type = "SERVICE_CONTROL_POLICY" if policy == "scp" else "TAG_POLICY"
            campaign = OrganizationPolicyApplicationCampaign(
                _type, organization_mapping
            )
            organizations.enable_organization_policies(_type)
            _policies = OrganizationPolicy._find_all_polices_v2(policy)
            LOGGER.info("Discovered the following policies: %s", _policies)
            # Compare policies in file(s) with current policy names from SSM
            # current_policies = []
            # try:
            #     current_policies = ast.literal_eval(
            #         parameter_store.fetch_parameter(f"{policy}-v2")
            #     )
            #     for stored_policy in current_policies:
            #         path = (
            #             OrganizationPolicy._trim_scp_file_name(stored_policy)
            #             if policy == "scp"
            #             else OrganizationPolicy._trim_tagging_policy_file_name(
            #                 stored_policy
            #             )
            #         )
            #         OrganizationPolicy.set_scp_attachment(
            #             config.get("scp"), organization_mapping, path, organizations
            #         )
            #         if stored_policy not in _policies:
            #             OrganizationPolicy.clean_and_remove_policy_attachment(
            #                 organization_mapping,
            #                 path,
            #                 organizations,
            #                 _type,
            #             )
            # except ParameterNotFoundError:
            #     LOGGER.debug(
            #         "Parameter %s was not found in Parameter Store, continuing.",
            #         policy,
            #     )
            #     pass

            for _policy in _policies:
                policy_definition = json.loads(Organizations.get_policy_body(_policy))
                # TODO: Schema validation here
                LOGGER.info(policy_definition)
                proposed_policy = policy_definition.get("Policy")
                proposed_policy_name = policy_definition.get("PolicyName")
                policy = campaign.get_policy(proposed_policy_name, proposed_policy)
                targets = policy_definition.get("targets", [])

                LOGGER.info(organization_mapping)
                policy.set_targets([campaign.get_target(t) for t in targets])
                for target in targets:
                    # For each target defined
                    # Check if it currently exists on the target

                    # If the policy doesn't exist, schedule it for attachment

                    # Pull current attachments from API? SSM?

                    policy_target = campaign.get_target(target)
                    proposed_policy_name = policy_definition.get("PolicyName")
                    existing_policy_id = policy_ids.get(proposed_policy_name)
                    if existing_policy_id:
                        current_policy = organizations.describe_policy(
                            existing_policy_id
                        )
                        if self._compare_ordered_policy(
                            current_policy.get("Content")
                        ) == self._compare_ordered_policy(proposed_policy):
                            LOGGER.info(
                                "Policy (%s) %s does not require updating. Path is: %s",
                                policy,
                                organization_mapping[target],
                                target,
                            )
                            continue
                        LOGGER.info(
                            "Policy (%s) will be updated for %s. Path is: %s",
                            policy,
                            organization_mapping[target],
                            target,
                        )
                        policy_target.update_policy(policy_id, proposed_policy)
                        continue
                    try:
                        policy_id = organizations.create_policy(
                            proposed_policy,
                            target,
                            _type,
                        )
                        LOGGER.info(
                            "Policy (%s) has been created for %s. Path is: %s",
                            policy,
                            organization_mapping[target],
                            target,
                        )
                        organizations.attach_policy(
                            policy_id,
                            organization_mapping[target],
                        )
                    except organizations.client.exceptions.DuplicatePolicyAttachmentException:
                        LOGGER.info(
                            "Policy (%s) for %s exists and is attached already.",
                            policy,
                            organization_mapping[target],
                        )
                    except organizations.client.exceptions.DuplicatePolicyException:
                        LOGGER.info(
                            "Policy (%s) for %s exists ensuring attached.",
                            policy,
                            organization_mapping[target],
                        )
                        policy_id = organizations.list_policies(
                            f"adf-{policy}-{target}",
                            _type,
                        )
                        organizations.attach_policy(
                            policy_id, organization_mapping[target]
                        )
            parameter_store.put_parameter(policy, str(_policies))
