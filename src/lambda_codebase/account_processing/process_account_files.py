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
import yaml

import boto3
from aws_xray_sdk.core import patch_all
from organizations import Organizations

patch_all()

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


def process_account(account_lookup, account):
    processed_account = account.copy()
    processed_account["needs_created"] = True
    account_id = account_lookup.get(account["account_full_name"])
    if account_id:
        processed_account["Id"] = account_id
        processed_account["needs_created"] = False
    return processed_account


def process_account_list(all_accounts, accounts_in_file):
    account_lookup = {account["Name"]: account["Id"] for account in all_accounts}
    processed_accounts = list(map(lambda account: process_account(account_lookup=account_lookup, account=account), accounts_in_file))
    # processed_accounts = [process_account(account_lookup, account) for account in accounts_in_file]
    return processed_accounts


def start_executions(sfn, processed_account_list):
    for account in processed_account_list:
        sfn.start_execution(
            stateMachineArn=ACCOUNT_MANAGEMENT_STATEMACHINE,
            input=f"{json.dumps(account)}",
        )

def lambda_handler(event, _):
    """Main Lambda Entry point"""
    sfn = boto3.client("stepfunctions")
    all_accounts = get_all_accounts()
    account_file = get_file_from_s3(get_details_from_event(event), boto3.resource("s3"))
    accounts = account_file.get("accounts")
    processed_account_list = process_account_list(all_accounts=all_accounts, accounts_in_file=accounts)

    start_executions(sfn, processed_account_list)
    return event
