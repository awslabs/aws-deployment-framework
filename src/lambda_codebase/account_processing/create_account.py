# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates an account within your organisation.
"""

import os
from aws_xray_sdk.core import patch_all
import boto3

patch_all()
ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")


def create_account(account, adf_role_name, org_client):
    allow_billing = "ALLOW" if account.get("allow_billing", False) else "DENY"
    response = org_client.create_account(
        Email=account.get("email"),
        AccountName=account.get("account_full_name"),
        RoleName=adf_role_name,  # defaults to OrganizationAccountAccessRole
        IamUserAccessToBilling=allow_billing,
    )["CreateAccountStatus"]
    while response["State"] == "IN_PROGRESS":
        response = org_client.describe_create_account_status(
            CreateAccountRequestId=response["Id"]
        )["CreateAccountStatus"]
        if response.get("FailureReason"):
            raise IOError(
                f"Failed to create account {account.get('account_full_name')}: {response['FailureReason']}"
            )
    account_id = response["AccountId"]
    account["Id"] = account_id
    return account


def lambda_handler(event, _):
    print(f"Creating account {event.get('account_full_name')}")
    org_client = boto3.client("organizations")
    return create_account(event, ADF_ROLE_NAME, org_client)
