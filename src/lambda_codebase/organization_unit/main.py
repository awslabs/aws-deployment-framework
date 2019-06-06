# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Organization Unit Main that is called when ADF is installed to create the deployment OU
"""

from typing import Mapping, Any, Tuple
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
OrgUnitId = str
CloudFormationResponse = Tuple[PhysicalResourceId, Data]

# Globals:
ORGANIZATION_CLIENT = boto3.client("organizations")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class InvalidPhysicalResourceId(Exception):
    pass


@dataclass
class PhysicalResource:
    org_unit_id: str
    org_unit_created: bool

    @classmethod
    def from_json(cls, json_string: PhysicalResourceId) -> "PhysicalResource":
        try:
            return cls(**json.loads(json_string))
        except json.JSONDecodeError as err:
            raise InvalidPhysicalResourceId from err

    def as_cfn_response(self) -> Tuple[PhysicalResourceId, Data]:
        physical_resource_id = json.dumps(asdict(self))
        data = {
            "OrganizationUnitId": self.org_unit_id,
            "OrganizationUnitCreated": json.dumps(self.org_unit_created),
        }
        return physical_resource_id, data


@create()
def create_(event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    parent_id = event["ResourceProperties"]["ParentId"]
    org_unit_name = event["ResourceProperties"]["OrganizationUnitName"]
    org_unit_id, created = ensure_org_unit(parent_id, org_unit_name)
    return PhysicalResource(org_unit_id, created).as_cfn_response()


@update()
def update_(event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    parent_id = event["ResourceProperties"]["ParentId"]
    org_unit_name = event["ResourceProperties"]["OrganizationUnitName"]
    org_unit_id, created = ensure_org_unit(parent_id, org_unit_name)
    return PhysicalResource(org_unit_id, created).as_cfn_response()


@delete()
def delete_(event: Mapping[str, Any], _context: Any):
    try:
        physical_resource = PhysicalResource.from_json(event["PhysicalResourceId"])
    except InvalidPhysicalResourceId:
        raw_physical_resource = event["PhysicalResourceId"]
        LOGGER.info(
            "Unrecognized physical resource: %s. Assuming no delete necessary", raw_physical_resource
        )
        return

    if physical_resource.org_unit_created:
        try:
            ORGANIZATION_CLIENT.delete_organizational_unit(
                OrganizationalUnitId=physical_resource.org_unit_id
            )
            LOGGER.info("Deleted OU")
        except ORGANIZATION_CLIENT.exceptions.OrganizationalUnitNotEmptyException:
            LOGGER.info("OU not empty –– skipping delete")
        except ORGANIZATION_CLIENT.exceptions.OrganizationalUnitNotFoundException:
            LOGGER.info("OU not found –– skipping delete")


def ensure_org_unit(parent_id: str, org_unit_name: str) -> Tuple[OrgUnitId, Created]:
    try:
        LOGGER.info("Creating OU %s with parent_id %s", org_unit_name, parent_id)
        create_org_unit = ORGANIZATION_CLIENT.create_organizational_unit(
            ParentId=parent_id, Name=org_unit_name
        )
        org_unit_id = create_org_unit["OrganizationalUnit"]["Id"]
        LOGGER.info("OU created: %s", org_unit_id)
        return org_unit_id, True
    except ORGANIZATION_CLIENT.exceptions.DuplicateOrganizationalUnitException:
        LOGGER.info("deployment OU already exists")
        pass

    params: dict = {"ParentId": parent_id}
    while True:
        org_units = ORGANIZATION_CLIENT.list_organizational_units_for_parent(**params)
        for org_unit in filter(
                lambda ou: ou["Name"] == org_unit_name, org_units["OrganizationalUnits"]
            ):
            org_unit_id = org_unit["Id"]
            LOGGER.info("OU already exists: %s", org_unit_id)
            return org_unit_id, False
        if not "NextToken" in org_units:
            raise Exception("Unable to find OU")
        params["NextToken"] = org_units["NextToken"]
