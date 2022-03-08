# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Listens to notifications from the adf-account-bucket
Identifies accounts that need to be created and then
invokes the account processing step function per account.
"""

import json
import os
import tempfile
import yaml
from yaml.error import YAMLError

import boto3
from botocore.exceptions import ClientError
from aws_xray_sdk.core import patch_all
from organizations import Organizations
from logger import configure_logger


patch_all()
LOGGER = configure_logger(__name__)
ACCOUNT_MANAGEMENT_STATEMACHINE = os.getenv("ACCOUNT_MANAGEMENT_STATEMACHINE_ARN")


def get_details_from_event(event: dict):
    s3_details = event.get("Records", [{}])[0].get("s3")
    if not s3_details:
        raise ValueError("No S3 Event details present in event trigger")
    bucket_name = s3_details.get("bucket", {}).get("name")
    object_key = s3_details.get("object", {}).get("key")
    return {
        "bucket_name": bucket_name,
        "object_key": object_key,
    }


def get_file_from_s3(s3_object: dict, s3_resource: boto3.resource):
    try:
        s3_object = s3_resource.Object(**s3_object)
        with tempfile.TemporaryFile(encoding='utf-8') as file_pointer:
            s3_object.download_fileobj(file_pointer)

            # Move pointer to the start of the file
            file_pointer.seek(0)

            return yaml.safe_load(file_pointer)
    except ClientError as error:
        LOGGER.error(
            f"Failed to download {s3_object.get('object_key')} "
            f"from {s3_object.get('bucket_name')}, due to {error}"
        )
        raise
    except YAMLError as yaml_error:
        LOGGER.error(
            f"Failed to parse YAML file: {s3_object.get('object_key')} "
            f"from {s3_object.get('bucket_name')}, due to {yaml_error}"
        )
        raise


def get_all_accounts():
    org_client = Organizations(boto3)
    return org_client.get_accounts()


def process_account(account_lookup, account):
    processed_account = account.copy()
    processed_account["needs_created"] = True
    account_id = account_lookup.get(account["account_full_name"])
    if account_id:
        processed_account["account_id"] = account_id
        processed_account["needs_created"] = False
    return processed_account


def process_account_list(all_accounts, accounts_in_file):
    account_lookup = {account["Name"]: account["Id"] for account in all_accounts}
    processed_accounts = list(map(
        lambda account: process_account(
            account_lookup=account_lookup,
            account=account,
        ),
        accounts_in_file
    ))
    return processed_accounts


def start_executions(sfn_client, processed_account_list):
    LOGGER.info(f"Invoking Account Management State Machine ({ACCOUNT_MANAGEMENT_STATEMACHINE})")
    for account in processed_account_list:
        LOGGER.debug(f"Payload: {account}")
        sfn_client.start_execution(
            stateMachineArn=ACCOUNT_MANAGEMENT_STATEMACHINE,
            input=f"{json.dumps(account)}",
        )


def lambda_handler(event, _):
    """Main Lambda Entry point"""
    sfn_client = boto3.client("stepfunctions")
    s3_resource = boto3.resource("s3")

    all_accounts = get_all_accounts()
    account_file = get_file_from_s3(get_details_from_event(event), s3_resource)

    processed_account_list = process_account_list(
        all_accounts=all_accounts,
        accounts_in_file=account_file.get("accounts"),
    )

    start_executions(sfn_client, processed_account_list)
    return event
