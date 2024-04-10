# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Moves an account to the specified OU.
"""
import boto3
from aws_xray_sdk.core import patch_all

# ADF imports
from logger import configure_logger
from organizations import Organizations


patch_all()
LOGGER = configure_logger(__name__)


def lambda_handler(event, _):
    LOGGER.info(
        "Ensuring Account: %s is in OU %s",
        event.get('account_full_name'),
        event.get('organizational_unit_path'),
    )
    organizations = Organizations(boto3)
    organizations.move_account(
        event.get("account_id"),
        event.get("organizational_unit_path"),
    )
    return event
