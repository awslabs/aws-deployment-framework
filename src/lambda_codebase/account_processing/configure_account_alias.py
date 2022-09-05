# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates or updates an ALIAS for an account
"""

import os
import json
import boto3
from sts import STS
from aws_xray_sdk.core import patch_all
from logger import configure_logger
from events import ADFEvents

patch_all()

LOGGER = configure_logger(__name__)
ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")
AWS_PARTITION = os.getenv("AWS_PARTITION")
EVENTS =  ADFEvents(boto3.client("events"), "AccountManagement")


def delete_account_aliases(account, iam_client, current_aliases):
    for alias in current_aliases:
        LOGGER.info(
            "Account %s, removing alias %s",
            account.get('account_full_name'),
            alias,
        )
        iam_client.delete_account_alias(AccountAlias=alias)


def create_account_alias(account, iam_client):
    LOGGER.info(
        "Adding alias to: %s alias %s",
        account.get('account_full_name'),
        account.get('alias'),
    )
    try:
        iam_client.create_account_alias(AccountAlias=account.get("alias"))
    except iam_client.exceptions.EntityAlreadyExistsException as error:
        LOGGER.error(
            f"The account alias {account.get('alias')} already exists."
            "The account alias must be unique across all Amazon Web Services "
            "products. Refer to "
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/"
            "console_account-alias.html#AboutAccountAlias"
        )
        raise error


def ensure_account_has_alias(account, iam_client):
    LOGGER.info(
        "Ensuring Account: %s has alias %s",
        account.get('account_full_name'),
        account.get('alias'),
    )
    current_aliases = iam_client.list_account_aliases().get('AccountAliases')
    if account.get('alias') in current_aliases:
        LOGGER.info(
            "Account: %s already has alias %s",
            account.get('account_full_name'),
            account.get('alias'),
        )
        return

    # Since you can only have one alias per account, lets
    # remove all old aliases (is at most one)
    delete_account_aliases(account, iam_client, current_aliases)
    create_account_alias(account, iam_client)


def lambda_handler(event, _):
    if event.get("alias"):
        sts = STS()
        account_id = event.get("account_id")
        role = sts.assume_cross_account_role(
            f"arn:{AWS_PARTITION}:iam::{account_id}:role/{ADF_ROLE_NAME}",
            "adf_account_alias_config",
        )
        ensure_account_has_alias(event, role.client("iam"))
        EVENTS.put_event(detail=json.dumps({"account_id": account_id, "alias_value": event.get("alias")}), detailType="ACCOUNT_ALIAS_CONFIGURED", resources=[account_id])
    else:
        LOGGER.info(
            "Account: %s does not need an alias",
            event.get('account_full_name'),
        )
    return event
