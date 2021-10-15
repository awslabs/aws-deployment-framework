# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Moves an account to the specified OU.
"""
from organizations import Organizations
import boto3
from aws_xray_sdk.core import patch_all

patch_all()


def lambda_handler(event, _):
    print(
        f"Ensuring Account: {event.get('account_full_name')} is in OU {event.get('organizational_unit_path')}"
    )
    organizations = Organizations(boto3)
    organizations.move_account(event.get("Id"), event.get("organizational_unit_path"))
    return event
