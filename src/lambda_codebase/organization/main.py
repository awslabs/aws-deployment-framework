# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Organization main that is called when ADF is installed to create the organization if required
"""

from typing import Mapping, Any, Tuple, cast
from dataclasses import dataclass, asdict
import logging
import json
import boto3
from cfn_custom_resource import (  # pylint: disable=unused-import
    lambda_handler,
    create,
    update,
    delete,
)

# Type aliases:
Data = Mapping[str, str]
PhysicalResourceId = str
Created = bool
OrganizationId = str
OrganizationRootId = str
CloudFormationResponse = Tuple[PhysicalResourceId, Data]

# Globals:
ORGANIZATION_CLIENT = boto3.client("organizations")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class InvalidPhysicalResourceId(Exception):
    pass


@dataclass
class PhysicalResource:
    organization_id: str
    created: bool
    organization_root_id: str

    @classmethod
    def from_json(cls, json_string: PhysicalResourceId) -> "PhysicalResource":
        try:
            return cls(**json.loads(json_string))
        except json.JSONDecodeError as err:
            raise InvalidPhysicalResourceId from err

    def as_cfn_response(self) -> Tuple[PhysicalResourceId, Data]:
        physical_resource_id = json.dumps(asdict(self))
        data = {
            "OrganizationId": self.organization_id,
            "OrganizationCreated": json.dumps(self.created),
            "OrganizationRootId": self.organization_root_id,
        }
        return physical_resource_id, data


@create()
def create_(_event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    organization_id, created = ensure_organization()
    organization_root_id = get_organization_root_id()
    return PhysicalResource(
        organization_id, created, organization_root_id
    ).as_cfn_response()


@update()
def update_(_event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    organization_id, created = ensure_organization()
    organization_root_id = get_organization_root_id()
    return PhysicalResource(
        organization_id, created, organization_root_id
    ).as_cfn_response()


@delete()
def delete_(event, _context):
    try:
        physical_resource = PhysicalResource.from_json(event["PhysicalResourceId"])
    except InvalidPhysicalResourceId:
        raw_physical_resource = event["PhysicalResourceId"]
        LOGGER.info(
            "Unrecognized physical resource: %s. Assuming no delete necessary",
            raw_physical_resource
        )
        return

    if physical_resource.created:
        try:
            ORGANIZATION_CLIENT.delete_organization()
            LOGGER.info("Deleted Organization")
        except ORGANIZATION_CLIENT.exceptions.OrganizationNotEmptyException:
            LOGGER.info("Organization not empty –– skipping delete")
        except ORGANIZATION_CLIENT.exceptions.AWSOrganizationsNotInUseException:
            LOGGER.info("Organization does not exist –– skipping delete")


def ensure_organization() -> Tuple[OrganizationId, Created]:
    try:
        describe_organization = ORGANIZATION_CLIENT.describe_organization()
    except ORGANIZATION_CLIENT.exceptions.AWSOrganizationsNotInUseException:
        create_organization = ORGANIZATION_CLIENT.create_organization(FeatureSet="ALL")
        organization_id = create_organization["Organization"]["Id"]
        LOGGER.info("Organization created: %s", organization_id)
        return organization_id, True

    if describe_organization["Organization"]["FeatureSet"] != "ALL":
        raise Exception(
            "Existing organization is only set up for CONSOLIDATED_BILLING, but ADF needs ALL features"
        )
    organization_id = describe_organization["Organization"]["Id"]
    LOGGER.info(
        "Organization exists (id: %s) and enabled for ALL features",
        organization_id
    )
    return organization_id, False


def get_organization_root_id() -> str:
    LOGGER.info("Determining ORG root id ...")
    params: dict = {}
    while True:
        roots = ORGANIZATION_CLIENT.list_roots(**params)
        if "Roots" in roots and roots["Roots"]:
            organization_root_id = roots["Roots"][0]["Id"]
            LOGGER.info("ORG root id is: %s", organization_root_id)
            return cast(str, organization_root_id)
        if not "NextToken" in roots:
            raise Exception("Unable to find ORG root id")
        params["next_token"] = roots["NextToken"]
