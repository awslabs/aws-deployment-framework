# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Gets all the default regions for an account.
"""

import os
from sts import STS
from aws_xray_sdk.core import patch_all
from logger import configure_logger

patch_all()

LOGGER = configure_logger(__name__)
ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")
AWS_PARTITION = os.getenv("AWS_PARTITION")

def get_default_regions_for_account(ec2_client):
    default_regions = [
    region["RegionName"]
    for region in ec2_client.describe_regions(
        AllRegions=False,
        Filters=[
            {
                "Name": "opt-in-status",
                "Values": [
                    "opt-in-not-required",
                    "opted-in"
                ],
            }
        ],
    )["Regions"]
    ]
    return default_regions


def lambda_handler(event, _):
    LOGGER.info("Fetching Default regions %s", event.get('account_full_name'))
    sts = STS()
    account_id = event.get("account_id")
    role = sts.assume_cross_account_role(
        f"arn:{AWS_PARTITION}:iam::{account_id}:role/{ADF_ROLE_NAME}",
        "adf_account_get_regions",
    )
    default_regions = get_default_regions_for_account(role.client("ec2"))

    LOGGER.debug("Default regions for %s: %s", account_id, default_regions)
    return {
        **event,
        "default_regions": default_regions,
    }
