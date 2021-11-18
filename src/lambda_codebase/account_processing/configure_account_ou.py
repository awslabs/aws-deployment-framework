# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Moves an account to the specified OU.
"""
from organizations import Organizations
import boto3
from aws_xray_sdk.core import patch_all
from logger import configure_logger


patch_all()
LOGGER = configure_logger(__name__)


def lambda_handler(event, _):
    LOGGER.info(
        f"Ensuring Account: {event.get('account_full_name')} is "
        f"in OU {event.get('organizational_unit_path')}"
    )
    organizations = Organizations(boto3)
    organizations.move_account(
        event.get("account_id"),
        event.get("organizational_unit_path"),
    )
    return event
