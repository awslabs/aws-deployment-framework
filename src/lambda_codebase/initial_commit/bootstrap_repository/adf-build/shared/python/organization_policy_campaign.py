# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Organizations Policy module used throughout the ADF.
"""

import os
import json
from typing import List
import boto3

from logger import configure_logger


LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv("AWS_REGION")
ENABLE_V2 = os.getenv("ENABLE_V2")
DEFAULT_POLICY_ID = "p-FullAWSAccess"

# pylint: disable=W1508. R1735, W0235, R1734, W1201


class OrganizationPolicyException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PolicyTargetNotFoundException(OrganizationPolicyException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

# pylint: disable=W1508. R1735, W0235, R1734, W1201, C0209
class OrganizationPolicyTarget:
    existing_policy_ids: dict()
    path: str
    type: str
    id: str
    config: dict()

    def __repr__(self) -> str:
        return f"{self.path} ({self.id}) ({self.type})"

    def __init__(
        self,
        target_path,
        policy_type,
        policy_id,
        config,
        organizations_client=None,
    ) -> None:

        self.path = target_path
        self.type = policy_type
        self.id = policy_id
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
        LOGGER.debug("Existing Policy Ids: %s", self.existing_policy_ids)
        if policy_id not in self.existing_policy_ids:
            self.organizations_client.attach_policy(
                PolicyId=policy_id, TargetId=self.id
            )
            self.existing_policy_ids[policy_id] = policy_name
        else:
            LOGGER.info(
                "Policy %s (%s) already attached to %s" %
                (policy_name, policy_id, self),
            )

        if (
            DEFAULT_POLICY_ID in self.existing_policy_ids.keys()
            and self.config.get("keep-default-scp", "enabled") == "disabled"
        ):
            self.organizations_client.detach_policy(
                PolicyId=DEFAULT_POLICY_ID, TargetId=self.id
            )


# pylint: disable=W1508. R1735, W0235, R1734, W1201, W1203
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

    def __repr__(self) -> str:
        return f"{self.name} ({self.id}) ({self.type})"

    def __init__(
        self,
        policy_name,
        policy_body,
        policy_type,
        config,
        policy_id=None,
        policy_has_changed=False,
        organizations_client=None,
    ):
        self.name = policy_name
        self.body = policy_body
        self.id = policy_id
        self.type = policy_type
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
            try:
                current_targets = [
                    t.get("TargetId")
                    for t in self.organizations_client.list_targets_for_policy(
                        PolicyId=self.id
                    ).get("Targets")
                ]
                return current_targets
            except (
                self.organizations_client.exceptions.AccessDeniedException
            ) as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Access Denied"
                    % (self.name.self.id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    f"Error fetching targets for policy {self.name} {self.id}: Access Denied"
                ) from e
            except (
                self.organizations_client.exceptions.AWSOrganizationsNotInUseException
            ) as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Organizations not in use"
                    % (self.name.self.id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    "Organizations not in use"
                ) from e
            except (
                self.organizations_client.exceptions.InvalidInputException
            ) as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Invalid Input"
                    % (self.name.self.id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    f"Error fetching targets for policy {self.name} {self.id}: Invalid Input"
                ) from e
            except self.organizations_client.exceptions.ServiceException as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Service Exception" %
                    (self.name.self.id),
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    f"Error fetching targets for policy {self.name} {self.id}: Service Exception "
                ) from e
            except (
                self.organizations_client.exceptions.TooManyRequestsException
            ) as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Access Denied"
                    % (self.name.self.id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    "Too Many Requests to Organizations API"
                ) from e
            except Exception as e:
                LOGGER.critical(
                    "Error fetching targets for policy %s %s: Unexpected exception",
                    self.name,
                    self.id,
                )
                LOGGER.error(e)
                raise e
        else:
            return []

    def set_targets(self, targets):
        target: OrganizationPolicyTarget
        LOGGER.info("Current targets: %s", self.current_targets)
        for target in targets:
            if target.id in self.current_targets:
                LOGGER.info(
                    "%s already exists as a target for policy: %s",
                    target.id,
                    self.name,
                )
                self.targets_not_scheduled_for_deletion.append(target.id)
                continue
            LOGGER.info(
                "%s is not a target for: %s, marking it for attachment",
                target.id,
                self.name,
            )
            self.targets_requiring_attachment[target.id] = target

    def update_targets(self):
        if self.targets_requiring_attachment.values():
            LOGGER.info(
                "Attaching the policy (%s) to the following targets: %s",
                self.name,
                self.targets_requiring_attachment,
            )
        for target in self.targets_requiring_attachment.values():
            target.attach_policy(self.id, self.name)

        targets_to_detach = set(self.current_targets) - set(
            self.targets_not_scheduled_for_deletion
        )

        if targets_to_detach:
            LOGGER.info(
                "Removing the policy (%s) from the following targets: %s",
                self.name,
                targets_to_detach,
            )

        for target_id in targets_to_detach:
            LOGGER.info(
                "Detaching policy (%s) from target (%s)", self.name, target_id
            )
            try:
                self.organizations_client.detach_policy(
                    PolicyId=self.id, TargetId=target_id
                )
            except (
                self.organizations_client.exceptions.AccessDeniedException
            ) as e:
                LOGGER.critical(
                    "Error detaching policy %s (%s) from target %s: Access Denied" %
                    (self.name, self.id, target_id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    f"Error detaching policy: {self.name} {self.id} from {target_id}: Access Denied"
                ) from e
            except (
                self.organizations_client.exceptions.PolicyNotAttachedException
            ) as e:
                LOGGER.warning(
                    "Error detaching policy %s (%s) from target %s: Policy Not Attached" %
                    (self.name, self.id, target_id)
                )
                LOGGER.info(e)
                return
            except (
                self.organizations_client.exceptions.TargetNotFoundException
            ) as e:
                LOGGER.critical(
                    "Error detaching policy %s (%s) from target %s: Target Not Found" %
                    (self.name, self.id, target_id)
                )
                LOGGER.error(e)
                raise OrganizationPolicyException(
                    f"Error detaching policy {self.name} {self.id}: Target {target_id} Not Found"
                ) from e
            except Exception as e:
                LOGGER.critical(
                    "Error detaching policy %s %s: Unexpected Exception" %
                    (self.name, self.id)
                )
                LOGGER.error(e)
                raise e

    def create(self):
        policy_type_name = (
            "scp" if self.type == "SERVICE_CONTROL_POLICY" else "tagging-policy"
        )
        try:
            self.id = (
                self.organizations_client.create_policy(
                    Content=json.dumps(self.body),
                    Description=f"ADF Managed {policy_type_name}",
                    Name=self.name,
                    Type=self.type,
                )
                .get("Policy")
                .get("PolicySummary")
                .get("Id")
            )
        except self.organizations_client.exceptions.AccessDeniedException as e:
            LOGGER.critical(f"Error creating policy {self.name}: Access Denied")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Access Denied"
            ) from e
        except (
            self.organizations_client.exceptions.ConcurrentModificationException
        ) as e:
            LOGGER.critical(
                f"Error creating policy {self.name}: Concurrent Modification Ongoing"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Concurrent Modification Ongoing"
            ) from e
        except (
            self.organizations_client.exceptions.ConstraintViolationException
        ) as e:
            LOGGER.critical(
                f"Error creating policy {self.name}: Constraint Violation"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Constraint Violation"
            ) from e
        except (
            self.organizations_client.exceptions.DuplicatePolicyException
        ) as e:
            LOGGER.warning(
                f"Error creating policy {self.name}: Duplicate Policy"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Duplicate Policy"
            ) from e
        except self.organizations_client.exceptions.InvalidInputException as e:
            LOGGER.warning(f"Error creating policy {self.name}: Invalid Input")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Invalid Input"
            ) from e
        except (
            self.organizations_client.exceptions.MalformedPolicyDocumentException
        ) as e:
            LOGGER.warning(
                f"Error creating policy {self.name}: Policy Content Malformed"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Error creating policy {self.name}: Policy Content Malformed"
            ) from e
        except Exception as e:
            LOGGER.critical(
                f"Error creating policy {self.name}: Unexpected Exception"
            )
            LOGGER.error(e)
            raise e
        LOGGER.info("Policy %s created with id: %s", self.name, self.id)
        self.update_targets()

    def update(self):
        if self.policy_has_changed:
            LOGGER.info(
                "Policy %s has changed. Updating the policy with new content",
                self.name,
            )
            self.organizations_client.update_policy(
                PolicyId=self.id, Content=json.dumps(self.body)
            )
        self.update_targets()

    def delete(self):
        self.update_targets()
        self.organizations_client.delete_policy(PolicyId=self.id)


# pylint: disable=W1508. R1735, W0235, R1734, W1201, W1203
class OrganizationPolicyApplicationCampaign:
    targets: dict()
    campaign_config: dict()
    type: str
    organizational_mapping: dict
    policies_to_be_created: List[OrganizationalPolicyCampaignPolicy]
    policies_to_be_updated: List[OrganizationalPolicyCampaignPolicy]
    policies_to_be_deleted: List[OrganizationalPolicyCampaignPolicy]

    def __init__(
        self,
        policy_type,
        organizational_mapping,
        campaign_config,
        organizations_client,
    ) -> None:
        self.targets = {}
        self.type = policy_type
        self.organizational_mapping = organizational_mapping
        self.organizations = organizations_client
        self.policies_to_be_created = []
        self.policies_to_be_updated = []
        self.policies_to_be_deleted = []
        self.existing_policy_lookup = self.get_existing_policies()
        self.campaign_config = campaign_config

    def get_existing_policies(self):
        try:
            # TODO: Implement paginator here
            response = self.organizations.list_policies(Filter=self.type)
        except self.organizations.exceptions.AccessDeniedException as e:
            LOGGER.critical("Error fetching existing policies: Access Denied")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Access Denied when fetching existing policies ({self.type})"
            ) from e
        except (
            self.organizations.exceptions.AWSOrganizationsNotInUseException
        ) as e:
            LOGGER.critical(
                "Error fetching existing policies: AWS Orgs not in use"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException("Organizations not in use") from e
        except self.organizations.exceptions.InvalidInputException as e:
            LOGGER.critical("Error fetching existing policies: Invalid Input")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Invalid input fetching existing policies: {self.type}"
            ) from e
        except self.organizations.exceptions.ServiceException as e:
            LOGGER.critical(
                "Error fetching existing policies: Service Exception"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                "Service Error when fetching existing Org Policies"
            ) from e
        except self.organizations.exceptions.TooManyRequestsException as e:
            LOGGER.critical(
                "Error fetching existing policies: Too Many Requests"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException(
                "Too Many Requests to Organizations API"
            ) from e
        except Exception as e:
            LOGGER.critical(
                "Unexpected exception when fetching existing policies"
            )
            LOGGER.error(e)
            raise e

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
            try:
                self.targets[target] = OrganizationPolicyTarget(
                    target_path=target,
                    policy_type=self.type,
                    policy_id=self.organizational_mapping[target],
                    config=self.campaign_config,
                    organizations_client=self.organizations,
                )
            except KeyError as e:
                LOGGER.critical(
                    f"The target {e} was not found in the OU target Map"
                )
                LOGGER.info("Current OU map: %s", self.organizational_mapping)
                raise PolicyTargetNotFoundException(
                    f"The target {e} was not found in the OU target Map"
                ) from e
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
        current_policy = {}
        try:
            current_policy = json.loads(
                self.organizations.describe_policy(
                    PolicyId=self.existing_policy_lookup[policy_name]
                )
                .get("Policy")
                .get("Content")
            )
        except self.organizations.exceptions.AccessDeniedException as e:
            LOGGER.critical("Error describing existing policy: Access Denied")
            LOGGER.error(e)
            policy_id = self.existing_policy_lookup[policy_name]
            raise OrganizationPolicyException(
                f"Access Denied when fetching policy : {policy_name}{policy_id} ({self.type})"
            ) from e
        except (
            self.organizations.exceptions.AWSOrganizationsNotInUseException
        ) as e:
            LOGGER.critical(
                "Error describing existing policy: AWS Orgs not in use"
            )
            LOGGER.error(e)
            raise OrganizationPolicyException("Organizations not in use") from e
        except self.organizations.exceptions.InvalidInputException as e:
            LOGGER.critical("Error fetching existing policies: Invalid Input")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Invalid input fetching existing policy: {self.type}"
            ) from e
        except self.organizations.exceptions.ServiceException as e:
            LOGGER.critical("Error fetching existing policy: Service Exception")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                f"Service Error when fetching existing policy {policy_name}"
            ) from e
        except self.organizations.exceptions.TooManyRequestsException as e:
            LOGGER.critical("Error describing policy: Too Many Requests")
            LOGGER.error(e)
            raise OrganizationPolicyException(
                "Too Many Requests to Organizations API"
            ) from e
        except Exception as e:  # pylint: disable=W0703
            LOGGER.critical(
                "Unexpected exception when describing existing policy"
            )
            LOGGER.error(e)

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

    def delete_policy(self, policy_name):
        if policy_name in self.existing_policy_lookup:
            policy = OrganizationalPolicyCampaignPolicy(
                policy_name,
                {},
                self.type,
                self.campaign_config,
                self.existing_policy_lookup[policy_name],
                False,
                self.organizations,
            )
            self.policies_to_be_deleted.append(policy)

    def apply(self):
        if self.policies_to_be_created:
            LOGGER.info(
                "The following policies need to be created: %s",
                [policy.name for policy in self.policies_to_be_created],
            )
        for policy in self.policies_to_be_created:
            policy.create()

        if self.policies_to_be_updated:
            LOGGER.info(
                "The following policies (may) need to be updated: %s",
                [policy.name for policy in self.policies_to_be_updated],
            )
        for policy in self.policies_to_be_updated:
            policy.update()

        policies_defined_from_files = {
            policy.name for policy in self.policies_to_be_updated
        }

        adf_managed_policy_names = set(self.existing_policy_lookup.keys())
        self.policies_to_be_deleted.extend(
            [
                OrganizationalPolicyCampaignPolicy(
                    p,
                    {},
                    self.type,
                    self.campaign_config,
                    self.existing_policy_lookup[p],
                    False,
                    self.organizations,
                )
                for p in adf_managed_policy_names - policies_defined_from_files
            ]
        )
        if self.policies_to_be_deleted:
            LOGGER.info(
                "The following will be deleted as they are no longer defined in a file: %s",
                self.policies_to_be_deleted,
            )

        for policy in self.policies_to_be_deleted:
            policy.delete()
