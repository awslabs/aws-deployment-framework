# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Gets all the default regions for an account.
"""

import os
from aws_xray_sdk.core import patch_all

# ADF imports
from logger import configure_logger
from sts import STS

patch_all()

LOGGER = configure_logger(__name__)
ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME = os.getenv(
    "ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME",
)
AWS_PARTITION = os.getenv("AWS_PARTITION")
MANAGEMENT_ACCOUNT_ID = os.getenv('MANAGEMENT_ACCOUNT_ID')


def get_default_regions_for_account(ec2_client):
    filtered_regions = ec2_client.describe_regions(
        AllRegions=False,
        Filters=[
            {
                "Name": "opt-in-status",
                "Values": [
                    "opt-in-not-required",
                    "opted-in",
                ],
            },
        ],
    )["Regions"]
    default_regions = [region["RegionName"] for region in filtered_regions]
    return default_regions


def lambda_handler(event, _):
    LOGGER.info("Fetching Default regions %s", event.get("account_full_name"))
    sts = STS()
    account_id = event.get("account_id")
    role = sts.assume_bootstrap_deployment_role(
        AWS_PARTITION,
        MANAGEMENT_ACCOUNT_ID,
        account_id,
        ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME,
        "adf_account_get_regions",
    )
    default_regions = get_default_regions_for_account(role.client("ec2"))

    LOGGER.debug("Default regions for %s: %s", account_id, default_regions)
    return {
        **event,
        "default_regions": default_regions,
    }
