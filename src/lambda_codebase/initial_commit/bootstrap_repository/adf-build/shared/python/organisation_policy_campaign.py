# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy module used throughout the ADF.
"""

import os
import json
import boto3

from logger import configure_logger
from typing import List

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")
ENABLE_V2 = os.getenv("ENABLE_V2", True)


class OrganizationPolicyTarget:
    existing_policy_ids: dict()
    path: str
    type: str
    id: str
    config: dict()

    def __repr__(self) -> str:
        return f"{self.path} ({self.id}) ({self.type})"

    def __init__(
        self, target_path, type, id, config, organizations_client=None
    ) -> None:

        self.path = target_path
        self.type = type
        self.id = id
        self.config = config
        self.organizations_client = (
            organizations_client
            if organizations_client
            else boto3.client("organizations")
        )
        self.existing_policy_ids = self.get_existing_policies()

    def get_existing_policies(self):
        existing_policy_ids = {
            p["Id"]: p["Name"]
            for p in self.organizations_client.list_policies_for_target(
                TargetId=self.id, Filter=self.type
            ).get("Policies")
        }
        return existing_policy_ids

    def attach_policy(self, policy_id, policy_name):
        LOGGER.info("Existing Policy Ids: %s", self.existing_policy_ids)
        if policy_id not in self.existing_policy_ids:
            self.organizations_client.attach_policy(
                PolicyId=policy_id, TargetId=self.id
            )
            self.existing_policy_ids[policy_id] = policy_name
        else:
            LOGGER.info(
                f"Policy {policy_name} ({policy_id}) already attached to {self}"
            )
        if (
            "p-FullAWSAccess" in self.existing_policy_ids.keys()
            and self.config.get("keep-default-scp", "enabled") == "disabled"
        ):
            self.organizations_client.detach_policy(
                PolicyId="p-FullAWSAccess", TargetId=self.id
            )


class OrganizationalPolicyCampaignPolicy:
    name: str
    body: str
    id: str
    type: str
    campaign_config: dict()
    current_targets: list()
    targets_requiring_attachment: dict()
    policy_has_changed: bool
    targets_not_scheduled_for_deletion: list()

    def __str__(self) -> str:
        return f"{self.name} ({self.id}) ({self.type})"

    def __init__(
        self,
        policy_name,
        policy_body,
        type,
        config,
        id=None,
        policy_has_changed=False,
        organizations_client=None,
    ):
        self.name = policy_name
        self.body = policy_body
        self.id = id
        self.type = type
        self.campaign_config = config
        self.organizations_client = (
            organizations_client
            if organizations_client
            else boto3.client("organizations")
        )
        self.current_targets = self.get_current_targets_for_policy()
        self.targets_requiring_attachment = {}
        self.policy_has_changed = policy_has_changed
        self.targets_not_scheduled_for_deletion = []

    def get_current_targets_for_policy(self):
        if self.id:
            current_targets = [
                t.get("TargetId")
                for t in self.organizations_client.list_targets_for_policy(
                    PolicyId=self.id
                ).get("Targets")
            ]
            return current_targets
        else:
            return []

    def set_targets(self, targets):
        target: OrganizationPolicyTarget
        LOGGER.info("Current targets: %s", self.current_targets)
        for target in targets:
            if target.id in self.current_targets:
                LOGGER.info(
                    "%s already exists as a target for policy: %s", target.id, self.name
                )
                self.targets_not_scheduled_for_deletion.append(target.id)
                continue
            else:
                LOGGER.info(
                    "%s is not a target for: %s, marking it for attachment",
                    target.id,
                    self.name,
                )
                self.targets_requiring_attachment[target.id] = target

    def update_targets(self):
        LOGGER.info(
            "Attaching the policy (%s) to the following targets: %s",
            self.name,
            self.targets_requiring_attachment,
        )
        for target in self.targets_requiring_attachment.values():
            LOGGER.info(type(target))
            target.attach_policy(self.id, self.name)

        targets_to_detach = set(self.current_targets) - set(
            self.targets_not_scheduled_for_deletion
        )
        LOGGER.info(
            "Removing the policy (%s) from the following targets: %s",
            self.name,
            targets_to_detach,
        )

        for target_id in targets_to_detach:
            LOGGER.info("Detaching policy (%s) from target (%s)", self.name, target_id)
            self.organizations_client.detach_policy(
                PolicyId=self.id, TargetId=target_id
            )

    def create(self):
        policy_type_name = (
            "scp" if self.type == "SERVICE_CONTROL_POLICY" else "tagging-policy"
        )
        response = self.organizations_client.create_policy(
            Content=json.dumps(self.body),
            Description=f"ADF Managed {policy_type_name}",
            Name=self.name,
            Type=self.type,
        )

        self.id = response.get("Policy").get("PolicySummary").get("Id")
        LOGGER.info("Policy %s created with id: %s", self.name, self.id)
        self.update_targets()

    def update(self):
        if self.policy_has_changed:
            LOGGER.info(
                "Policy %s has changed. Updating the policy with new content", self.name
            )
            self.organizations_client.update_policy(
                PolicyId=self.id, Content=json.dumps(self.body)
            )
        self.update_targets()

    def delete(self):
        pass


class OrganizationPolicyApplicationCampaign:
    targets: dict()
    campaign_config: dict()
    type: str
    organizational_mapping: dict
    policies_to_be_created: List[OrganizationalPolicyCampaignPolicy]
    policies_to_be_updated: List[OrganizationalPolicyCampaignPolicy]

    def __init__(
        self, type, organizational_mapping, campaign_config, organisations_client
    ) -> None:
        self.targets = {}
        self.type = type
        self.organizational_mapping = organizational_mapping
        self.organizations = organisations_client
        self.policies_to_be_created = []
        self.policies_to_be_updated = []
        self.existing_policy_lookup = self.get_existing_policys()
        self.campaign_config = campaign_config

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
                config=self.campaign_config,
                organizations_client=self.organizations,
            )
        return self.targets[target]

    def get_policy(self, policy_name, policy_body):
        if policy_name not in self.existing_policy_lookup:
            return self.create_policy(policy_name, policy_body)
        return self.update_policy(policy_name, policy_body)

    def create_policy(self, policy_name, policy_body):
        policy = OrganizationalPolicyCampaignPolicy(
            policy_name,
            policy_body,
            self.type,
            self.campaign_config,
            None,
            True,
            self.organizations,
        )
        self.policies_to_be_created.append(policy)
        return policy

    def update_policy(self, policy_name, policy_body):

        current_policy = json.loads(
            self.organizations.describe_policy(
                PolicyId=self.existing_policy_lookup[policy_name]
            )
            .get("Policy")
            .get("Content")
        )

        policy_has_changed = current_policy != policy_body
        policy = OrganizationalPolicyCampaignPolicy(
            policy_name,
            policy_body,
            self.type,
            self.campaign_config,
            self.existing_policy_lookup[policy_name],
            policy_has_changed,
            self.organizations,
        )
        self.policies_to_be_updated.append(policy)

        return policy

    def apply(self):
        LOGGER.info(
            "The following policies need to be created: %s",
            [policy.name for policy in self.policies_to_be_created],
        )
        for policy in self.policies_to_be_created:
            policy.create()
        LOGGER.info(
            "The following policies (may) need to be updated: %s",
            [policy.name for policy in self.policies_to_be_updated],
        )
        for policy in self.policies_to_be_updated:
            policy.update()
