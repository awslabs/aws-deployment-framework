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


def lambda_handler(event, _):
    LOGGER.info(f"Fetching Default regions {event.get('account_full_name')}")
    sts = STS()
    account_id = event.get("account_id")
    role = sts.assume_cross_account_role(
        f"arn:aws:iam::{account_id}:role/{ADF_ROLE_NAME}",
        "adf_account_get_regions",
    )

    ec2_client = role.client("ec2")
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
    LOGGER.debug(f"Default regions for {account_id}: {default_regions}")
    return {
        **event,
        "default_regions": default_regions,
    }
