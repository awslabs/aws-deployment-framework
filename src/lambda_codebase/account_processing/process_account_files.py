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
import logging
from typing import Any, TypedDict
import yaml

from yaml.error import YAMLError

import boto3
from botocore.exceptions import ClientError
from aws_xray_sdk.core import patch_all
from organizations import Organizations
from logger import configure_logger


patch_all()
LOGGER = configure_logger(__name__)
ACCOUNT_MANAGEMENT_STATEMACHINE = os.getenv(
    "ACCOUNT_MANAGEMENT_STATEMACHINE_ARN",
)
ADF_VERSION = os.getenv("ADF_VERSION")
ADF_VERSION_METADATA_KEY = "adf_version"


class S3ObjectLocation(TypedDict):
    bucket_name: str
    key: str


class AccountFileData(TypedDict):
    """
    Class used to return YAML account file data and its related
    metadata like the execution_id of the CodePipeline that uploaded it.
    """
    content: Any
    execution_id: str


def get_details_from_event(event: dict) -> S3ObjectLocation:
    s3_details = event.get("Records", [{}])[0].get("s3")
    if not s3_details:
        raise ValueError("No S3 Event details present in event trigger")
    bucket_name = s3_details.get("bucket", {}).get("name")
    object_key = s3_details.get("object", {}).get("key")
    return {
        "bucket_name": bucket_name,
        "key": object_key,
    }


def get_file_from_s3(
    s3_object_location: S3ObjectLocation,
    s3_resource: boto3.resource,
) -> AccountFileData:
    try:
        LOGGER.debug(
            "Reading YAML from S3: %s from %s",
            s3_object_location.get('object_key'),
            s3_object_location.get('bucket_name'),
        )
        s3_object = s3_resource.Object(**s3_object_location)
        object_adf_version = s3_object.metadata.get(
            ADF_VERSION_METADATA_KEY,
            "n/a",
        )
        if object_adf_version != ADF_VERSION:
            LOGGER.info(
                "Skipping S3 object: %s as it is generated with "
                "an older ADF version ('adf_version' metadata = '%s')",
                s3_object_location,
                object_adf_version,
            )
            return {
                "content": {},
                "execution_id": ""
            }

        with tempfile.TemporaryFile(mode='w+b') as file_pointer:
            s3_object.download_fileobj(file_pointer)

            # Move pointer to the start of the file
            file_pointer.seek(0)

            return {
                "content": yaml.safe_load(file_pointer),
                "execution_id": s3_object.metadata.get("execution_id"),
            }
    except ClientError as error:
        LOGGER.error(
            "Failed to download %s from %s, due to %s",
            s3_object_location.get('object_key'),
            s3_object_location.get('bucket_name'),
            error,
        )
        raise
    except YAMLError as yaml_error:
        LOGGER.error(
            "Failed to parse YAML file: %s from %s, due to %s",
            s3_object_location.get('object_key'),
            s3_object_location.get('bucket_name'),
            yaml_error,
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
    account_lookup = {
        account["Name"]: account["Id"] for account in all_accounts
    }
    processed_accounts = list(map(
        lambda account: process_account(
            account_lookup=account_lookup,
            account=account,
        ),
        accounts_in_file
    ))
    return processed_accounts


def start_executions(
    sfn_client,
    processed_account_list,
    codepipeline_execution_id: str,
    request_id: str,
):
    if not codepipeline_execution_id:
        codepipeline_execution_id = "no-codepipeline-exec-id-found"
    short_request_id = request_id[-12:]
    run_id = f"{codepipeline_execution_id}-{short_request_id}"
    LOGGER.info(
        "Invoking Account Management State Machine (%s) -> %s",
        ACCOUNT_MANAGEMENT_STATEMACHINE,
        run_id,
    )
    for account in processed_account_list:
        full_account_name = account.get('account_full_name', 'no-account-name')
        # AWS Step Functions supports max 80 characters.
        # Since the run_id equals 49 characters plus the dash, we have 30
        # characters available. To ensure we don't run over, lets use a
        # truncated version instead:
        truncated_account_name = full_account_name[:30]
        sfn_execution_name = f"{truncated_account_name}-{run_id}"

        LOGGER.debug(
            "Payload for %s: %s",
            sfn_execution_name,
            account,
        )
        sfn_client.start_execution(
            stateMachineArn=ACCOUNT_MANAGEMENT_STATEMACHINE,
            name=sfn_execution_name,
            input=f"{json.dumps(account)}",
        )


def lambda_handler(event, context):
    """Main Lambda Entry point"""
    LOGGER.debug(
        "Processing event: %s",
        json.dumps(event, indent=2) if LOGGER.isEnabledFor(logging.DEBUG)
        else "--data-hidden--"
    )
    sfn_client = boto3.client("stepfunctions")
    s3_resource = boto3.resource("s3")

    all_accounts = get_all_accounts()
    account_file = get_file_from_s3(get_details_from_event(event), s3_resource)

    processed_account_list = process_account_list(
        all_accounts=all_accounts,
        accounts_in_file=account_file.get("content", {}).get("accounts", []),
    )

    if processed_account_list:
        start_executions(
            sfn_client,
            processed_account_list,
            codepipeline_execution_id=account_file.get("execution_id"),
            request_id=context.aws_request_id,
        )
    return event
