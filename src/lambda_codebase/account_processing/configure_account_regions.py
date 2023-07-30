# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Takes regions that the account is not-opted into and opts into them.
"""
from ast import literal_eval


import boto3
from aws_xray_sdk.core import patch_all
from logger import configure_logger

patch_all()
LOGGER = configure_logger(__name__)


def get_regions_from_ssm(ssm_client):
    regions = ssm_client.get_parameter(Name="target_regions")["Parameter"].get("Value")
    regions = literal_eval(regions)
    return regions


def get_region_status(account_client, **list_region_args):
    region_status_response = account_client.list_regions(**list_region_args)
    region_status = {
        region.get("RegionName"): region.get("RegionOptStatus")
        for region in region_status_response.get("Regions")
    }
    # Currently no built in paginator for list_regions...
    # So we have to do this manually.
    next_token = region_status_response.get("NextToken")
    if next_token:
        while next_token:
            list_region_args["NextToken"] = next_token
            region_status_response = account_client.list_regions(**list_region_args)
            next_token = region_status_response.get("NextToken")
            region_status = region_status | {
                region.get("RegionName"): region.get("RegionOptStatus")
                for region in region_status_response.get("Regions")
            }
    return region_status


def enable_regions_for_account(
    account_client, account_id, desired_regions, org_root_account_id
):
    list_region_args = {}
    enable_region_args = {}
    target_is_different_account = org_root_account_id != account_id
    if target_is_different_account:
        list_region_args["AccountId"] = account_id
        enable_region_args["AccountId"] = account_id

    region_status = get_region_status(account_client, **list_region_args)

    regions_enabled = {}
    for region in desired_regions:
        regions_enabled[region] = False
        desired_region_status = region_status.get(region.lower())
        if not desired_region_status:
            LOGGER.warning("Unable to obtain status of %s, not enabling")
        if desired_region_status == "DISABLED":
            LOGGER.info("Enabling Region %s because it is currently Disabled", region)
            enable_region_args["RegionName"] = region.lower()
            account_client.enable_region(**enable_region_args)
        else:
            LOGGER.info(
                "Not enabling Region: %s because it is: %s",
                region,
                desired_region_status,
            )
            if desired_region_status in ["ENABLED_BY_DEFAULT", "ENABLED"]:
                regions_enabled[region] = True
    LOGGER.info(regions_enabled)
    return all(regions_enabled.values())


def lambda_handler(event, _):
    desired_regions = []
    if event.get("regions"):
        LOGGER.info(
            "Account Level Regions is not currently supported."
            "Ignoring these values for now and using SSM only"
        )
    desired_regions.extend(get_regions_from_ssm(boto3.client("ssm")))
    org_root_account_id = boto3.client("sts").get_caller_identity().get("Account")
    target_account_id = event.get("account_id")
    LOGGER.info(
        "Target Account Id: %s - This is running in %s. These are the same: %s",
        target_account_id,
        org_root_account_id,
        target_account_id == org_root_account_id,
    )
    all_regions_enabled = enable_regions_for_account(
        boto3.client("account"),
        target_account_id,
        desired_regions,
        org_root_account_id,
    )
    event["all_regions_enabled"] = all_regions_enabled

    return event
