# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Creates an account within your organization.
"""

import os
from aws_xray_sdk.core import patch_all
import boto3

# ADF imports
from logger import configure_logger

patch_all()

LOGGER = configure_logger(__name__)
ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME = os.getenv("ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME")


def create_account(account, adf_privileged_role_name, org_client):
    LOGGER.info("Creating account %s", account.get('account_full_name'))
    allow_billing = "ALLOW" if account.get("allow_billing", False) else "DENY"
    response = org_client.create_account(
        Email=account.get("email"),
        AccountName=account.get("account_full_name"),
        RoleName=adf_privileged_role_name,  # defaults to OrganizationAccountAccessRole
        IamUserAccessToBilling=allow_billing,
    )["CreateAccountStatus"]
    while response["State"] == "IN_PROGRESS":
        response = org_client.describe_create_account_status(
            CreateAccountRequestId=response["Id"]
        )["CreateAccountStatus"]
        if response.get("FailureReason"):
            raise IOError(
                f"Failed to create account {account.get('account_full_name')}: "
                f"{response['FailureReason']}"
            )
    return {
        **account,
        "account_id": response["AccountId"],
    }


def lambda_handler(event, _):
    org_client = boto3.client("organizations")
    return create_account(event, ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME, org_client)
