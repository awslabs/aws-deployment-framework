# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Listens to notifications from the adf-account-bucket
Identifies accounts that need to be created and then
invokes the account processing step function per account.
"""

import json
import os
from typing import Tuple
from aws_xray_sdk.core.patcher import patch
import yaml

from aws_xray_sdk.core import xray_recorder, patch_all

patch_all()

from organizations import Organizations

import boto3

ACCOUNT_MANAGEMENT_STATEMACHINE = os.getenv("ACCOUNT_MANAGEMENT_STATEMACHINE_ARN")


def get_details_from_event(event: dict):
    s3_details = event.get("Records", [{}])[0].get("s3")
    bucket_name = s3_details.get("bucket", {}).get("name")
    object_key = s3_details.get("object", {}).get("key")
    return bucket_name, object_key


def get_file_from_s3(s3_object: Tuple, s3_client: boto3.resource):
    bucket_name, object_key = s3_object
    s3_object = s3_client.Object(bucket_name, object_key)
    s3_object.download_file(f"/tmp/{object_key}")
    with open(f"/tmp/{object_key}", encoding="utf-8") as data_stream:
        data = yaml.safe_load(data_stream)

    return data


def get_all_accounts():
    org_client = Organizations(boto3)
    return org_client.get_accounts()


def lambda_handler(event, _):
    """Main Lambda Entry point"""
    all_accounts = get_all_accounts()
    account_file = get_file_from_s3(get_details_from_event(event), boto3.resource("s3"))
    accounts = account_file.get("accounts")
    for account in accounts:
        print(account["account_full_name"])
        try:
            account_id = next(
                acc["Id"]
                for acc in all_accounts
                if acc["Name"] == account["account_full_name"]
            )
            account["Id"] = account_id
            account["needs_created"] = False
        except StopIteration:  # If the account does not exist yet..
            account["needs_created"] = True
    sfn = boto3.client("stepfunctions")
    for account in accounts:
        sfn.start_execution(
            stateMachineArn=ACCOUNT_MANAGEMENT_STATEMACHINE,
            input=f"{json.dumps(account)}",
        )
    return event
