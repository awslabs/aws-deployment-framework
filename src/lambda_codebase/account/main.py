# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Account main that is called when ADF is installed to initially create the deployment account if required.
"""

from typing import Mapping, Any, Tuple
from dataclasses import dataclass, asdict
import logging
import time
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
AccountId = str
CloudFormationResponse = Tuple[PhysicalResourceId, Data]

# Globals:
ORGANIZATION_CLIENT = boto3.client("organizations")
SSM_CLIENT = boto3.client("ssm")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
MAX_RETRIES = 120  # => 120 retries * 5 seconds = 10 minutes


class InvalidPhysicalResourceId(Exception):
    pass


@dataclass
class PhysicalResource:
    account_id: str
    account_name: str
    account_email: str
    created: bool

    @classmethod
    def from_json(cls, json_string: PhysicalResourceId) -> "PhysicalResource":
        try:
            return cls(**json.loads(json_string))
        except json.JSONDecodeError as err:
            raise InvalidPhysicalResourceId from err

    def as_cfn_response(self) -> CloudFormationResponse:
        physical_resource_id = json.dumps(asdict(self))
        data = {
            "AccountId": self.account_id,
            "AccountName": self.account_name,
            "AccountEmail": self.account_email,
            "Created": json.dumps(self.created),
        }
        return physical_resource_id, data


@create()
def create_(event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    existing_account_id = event["ResourceProperties"]["ExistingAccountId"]
    account_name = event["ResourceProperties"]["AccountName"]
    account_email = event["ResourceProperties"]["AccountEmailAddress"]
    cross_account_access_role_name = event["ResourceProperties"][
        "CrossAccountAccessRoleName"
    ]
    account_id, created = ensure_account(
        existing_account_id, account_name, account_email, cross_account_access_role_name)
    return PhysicalResource(
        account_id, account_name, account_email, created
    ).as_cfn_response()


@update()
def update_(event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    existing_account_id = event["ResourceProperties"]["ExistingAccountId"]
    previously_created = PhysicalResource.from_json(
        event["PhysicalResourceId"]).created
    account_name = event["ResourceProperties"]["AccountName"]
    account_email = event["ResourceProperties"]["AccountEmailAddress"]
    cross_account_access_role_name = event["ResourceProperties"][
        "CrossAccountAccessRoleName"
    ]
    account_id, created = ensure_account(
        existing_account_id, account_name, account_email, cross_account_access_role_name)
    return PhysicalResource(
        account_id, account_name, account_email, created or previously_created
    ).as_cfn_response()


@delete()
def delete_(event, _context):
    try:
        physical_resource = PhysicalResource.from_json(
            event["PhysicalResourceId"])
    except InvalidPhysicalResourceId:
        raw_physical_resource = event["PhysicalResourceId"]
        LOGGER.info(
            "Unrecognized physical resource: %s. Assuming no delete necessary",
            raw_physical_resource,
        )
        return

    if physical_resource.created:
        return


def ensure_account(existing_account_id: str,
                   account_name: str,
                   account_email: str,
                   cross_account_access_role_name: str,
                   no_retries: int = 0) -> Tuple[AccountId, bool]:
    # If an existing account ID was provided, use that:
    if existing_account_id:
        return existing_account_id, False

    # If no existing account ID was provided, check if the ID is stores in
    # parameter store:
    try:
        get_parameter = SSM_CLIENT.get_parameter(Name="deployment_account_id")
        return get_parameter["Parameter"]["Value"], False
    except SSM_CLIENT.exceptions.ParameterNotFound:
        pass  # Carry on with creating the account

    # No existing account found: create one
    LOGGER.info("Creating account ...")
    try:
        create_account = ORGANIZATION_CLIENT.create_account(
            Email=account_email,
            AccountName=account_name,
            RoleName=cross_account_access_role_name,
            IamUserAccessToBilling="ALLOW",
        )
    except ORGANIZATION_CLIENT.exceptions.ConcurrentModificationException as err:
        return handle_concurrent_modification(
            err,
            existing_account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
            no_retries + 1,
        )

    request_id = create_account["CreateAccountStatus"]["Id"]
    LOGGER.info("Account creation requested, request ID: %s", request_id)

    return wait_on_account_creation(request_id)


def wait_on_account_creation(request_id: str) -> Tuple[AccountId, bool]:
    while True:
        account_status = ORGANIZATION_CLIENT.describe_create_account_status(
            CreateAccountRequestId=request_id
        )
        if account_status["CreateAccountStatus"]["State"] == "FAILED":
            reason = account_status["CreateAccountStatus"]["FailureReason"]
            raise Exception(f"Failed to create account because {reason}")
        if account_status["CreateAccountStatus"]["State"] == "IN_PROGRESS":
            LOGGER.info(
                "Account creation still in progress, waiting.. "
                "then calling again with %s",
                request_id)
            time.sleep(10)
        else:
            account_id = account_status["CreateAccountStatus"]["AccountId"]
            LOGGER.info("Account created: %s", account_id)
            return account_id, True


def handle_concurrent_modification(
    error: Exception,
    existing_account_id: str,
    account_name: str,
    account_email: str,
    cross_account_access_role_name: str,
    no_retries: int = 0,
) -> Tuple[AccountId, bool]:
    LOGGER.info("Attempt %d - hit %s", no_retries + 1, error)
    if no_retries > MAX_RETRIES:
        LOGGER.error(
            "Reached maximum number of retries to create the account. "
            "Raising error to abort the execution."
        )
        raise error
    time.sleep(5)
    return ensure_account(
        existing_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        no_retries + 1,
    )
