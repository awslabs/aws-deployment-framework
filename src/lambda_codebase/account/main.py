# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
The Account main that is called when ADF is installed to initially create the
deployment account if required.
"""

import os
from typing import Mapping, Any, Tuple
from dataclasses import dataclass, asdict
import logging
import time
import json
import boto3
from botocore.exceptions import ClientError
from cfn_custom_resource import (  # pylint: disable=unused-import
    create,
    update,
    delete,
)

# ADF Imports
from organizations import Organizations

# Type aliases:
Data = Mapping[str, str]
PhysicalResourceId = str
AccountId = str
CloudFormationResponse = Tuple[PhysicalResourceId, Data]

# Globals:
ORGANIZATION_CLIENT = boto3.client("organizations")
SSM_CLIENT = boto3.client("ssm")
TAGGING_CLIENT = boto3.client("resourcegroupstaggingapi")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(os.environ.get("ADF_LOG_LEVEL", logging.INFO))
logging.basicConfig(level=logging.INFO)
MAX_RETRIES = 120  # => 120 retries * 5 seconds = 10 minutes
DEPLOYMENT_OU_PATH = '/deployment'
DEPLOYMENT_ACCOUNT_ID_PARAM_PATH = "/adf/deployment_account_id"
SSM_PARAMETER_ADF_DESCRIPTION = (
    "DO NOT EDIT - Used by The AWS Deployment Framework"
)


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
        existing_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=False,
    )
    return PhysicalResource(
        account_id, account_name, account_email, created
    ).as_cfn_response()


@update()
def update_(event: Mapping[str, Any], _context: Any) -> CloudFormationResponse:
    existing_account_id = event["ResourceProperties"]["ExistingAccountId"]
    previously_created = PhysicalResource.from_json(event["PhysicalResourceId"]).created
    account_name = event["ResourceProperties"]["AccountName"]
    account_email = event["ResourceProperties"]["AccountEmailAddress"]
    cross_account_access_role_name = event["ResourceProperties"][
        "CrossAccountAccessRoleName"
    ]
    account_id, created = ensure_account(
        existing_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=True,
    )
    return PhysicalResource(
        account_id, account_name, account_email, created or previously_created
    ).as_cfn_response()


@delete()
def delete_(event, _context):
    try:
        physical_resource = PhysicalResource.from_json(event["PhysicalResourceId"])
    except InvalidPhysicalResourceId:
        raw_physical_resource = event["PhysicalResourceId"]
        LOGGER.info(
            "Unrecognized physical resource: %s. Assuming no delete necessary",
            raw_physical_resource,
        )
        return

    if physical_resource.created:
        return


def _set_deployment_account_id_parameter(deployment_account_id: str):
    SSM_CLIENT.put_parameter(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        Value=deployment_account_id,
        Description=SSM_PARAMETER_ADF_DESCRIPTION,
        Type="String",
        Overwrite=True,
    )


def _find_deployment_account_via_orgs_api() -> str:
    try:
        organizations = Organizations(
            org_client=ORGANIZATION_CLIENT,
            tagging_client=TAGGING_CLIENT,
        )
        accounts_found = organizations.get_accounts_in_path(
            DEPLOYMENT_OU_PATH,
        )
        active_accounts = list(filter(
            lambda account: account.get("Status") == "ACTIVE",
            accounts_found,
        ))
        number_of_deployment_accounts = len(active_accounts)
        if number_of_deployment_accounts > 1:
            raise RuntimeError(
                "Failed to determine Deployment account to setup, as "
                f"{number_of_deployment_accounts} AWS Accounts were found "
                f"in the {DEPLOYMENT_OU_PATH} organization unit (OU). "
                "Please ensure there is only one account in the "
                f"{DEPLOYMENT_OU_PATH} OU path. "
                "Move all AWS accounts you don't want to be bootstrapped as "
                f"the ADF deployment account out of the {DEPLOYMENT_OU_PATH} "
                "OU. In case there are no accounts in the "
                f"{DEPLOYMENT_OU_PATH} OU, ADF will automatically create a "
                "new AWS account for you, or move the deployment account as "
                "specified at install time of ADF to the respective OU.",
            )
        if number_of_deployment_accounts == 1:
            deployment_account_id = str(active_accounts[0].get("Id"))
            _set_deployment_account_id_parameter(deployment_account_id)
            return deployment_account_id
        LOGGER.debug(
            "No active AWS Accounts found in the %s OU path.",
            DEPLOYMENT_OU_PATH,
        )
    except ClientError as client_error:
        LOGGER.debug(
            "Retrieving the accounts in %s failed due to %s."
            "Most likely the %s OU does not exist, if so, you can ignore this "
            "error as it will create it later on automatically.",
            DEPLOYMENT_OU_PATH,
            str(client_error),
            DEPLOYMENT_OU_PATH,
        )
    return ""


def _find_deployment_account_via_ssm_params() -> str:
    try:
        get_parameter = SSM_CLIENT.get_parameter(
            Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        )
        return get_parameter["Parameter"]["Value"]
    except SSM_CLIENT.exceptions.ParameterNotFound:
        LOGGER.debug(
            "SSM Parameter at %s does not exist. This is expected behavior "
            "when you install ADF the first time or upgraded ADF while the "
            "parameter store path was changed.",
            DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        )
    return ""


def ensure_account(
    existing_account_id: str,
    account_name: str,
    account_email: str,
    cross_account_access_role_name: str,
    no_retries: int = 0,
    is_update: bool = False,
) -> Tuple[AccountId, bool]:
    # If an existing account ID was provided, use that:
    ssm_deployment_account_id = _find_deployment_account_via_ssm_params()
    if existing_account_id:
        LOGGER.info(
            "Using existing deployment account as specified %s.",
            existing_account_id,
        )
        if is_update and not ssm_deployment_account_id:
            LOGGER.info(
                "The %s param was not found, creating it as we are "
                "updating ADF",
                DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
            )
            _set_deployment_account_id_parameter(existing_account_id)
        return existing_account_id, False

    # If no existing account ID was provided, check if the ID is stored in
    # parameter store:
    if ssm_deployment_account_id:
        LOGGER.info(
            "Using deployment account as specified with param %s : %s.",
            DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
            ssm_deployment_account_id,
        )
        return ssm_deployment_account_id, False

    if is_update:
        # If no existing account ID was provided and Parameter Store did not
        # contain the account id, check if the /deployment OU exists and
        # whether that has a single account inside.
        deployment_account_id = _find_deployment_account_via_orgs_api()
        if deployment_account_id:
            LOGGER.info(
                "Using deployment account %s as found in AWS Organization %s.",
                deployment_account_id,
                DEPLOYMENT_OU_PATH,
            )
            _set_deployment_account_id_parameter(deployment_account_id)
            return deployment_account_id, False

        error_msg = (
            "When updating ADF should not be required to create a deployment "
            "account. If your previous installation failed and you try to fix "
            "it via an update, please delete the ADF stack first and run it "
            "as a fresh installation."
        )
        LOGGER.error(error_msg)
        raise RuntimeError(error_msg)

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
        return _handle_concurrent_modification(
            err,
            account_name,
            account_email,
            cross_account_access_role_name,
            no_retries + 1,
        )

    request_id = create_account["CreateAccountStatus"]["Id"]
    LOGGER.info("Account creation requested, request ID: %s", request_id)

    LOGGER.info("Waiting for account creation to complete...")
    deployment_account_id = _wait_on_account_creation(request_id)
    LOGGER.info("Account created, using %s", deployment_account_id)
    return deployment_account_id, True


def _wait_on_account_creation(request_id: str) -> AccountId:
    while True:
        account_status = ORGANIZATION_CLIENT.describe_create_account_status(
            CreateAccountRequestId=request_id
        )
        if account_status["CreateAccountStatus"]["State"] == "FAILED":
            reason = account_status["CreateAccountStatus"]["FailureReason"]
            raise RuntimeError(f"Failed to create account because {reason}")
        if account_status["CreateAccountStatus"]["State"] == "IN_PROGRESS":
            LOGGER.info(
                "Account creation still in progress, waiting.. "
                "then calling again with %s",
                request_id,
            )
            time.sleep(10)
        else:
            account_id = account_status["CreateAccountStatus"]["AccountId"]
            LOGGER.info("Account created: %s", account_id)
            return account_id


def _handle_concurrent_modification(
    error: Exception,
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
    existing_account_id = ""
    return ensure_account(
        existing_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        no_retries + 1,
    )
