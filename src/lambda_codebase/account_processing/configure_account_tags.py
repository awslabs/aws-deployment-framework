# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates or adds tags to an account.
Currently only appends new tags.
Will not delete tags that aren't
in the config file.
"""

from organizations import Organizations

import boto3
from aws_xray_sdk.core import patch_all
from logger import configure_logger

patch_all()
LOGGER = configure_logger(__name__)


def create_account_tags(account_id, tags, org_session: Organizations):
    LOGGER.info(
        f"Ensuring Account: {account_id} has tags: {tags}"
    )
    org_session.create_account_tags(account_id, tags)


def lambda_handler(event, _):
    if event.get("tags"):
        organizations = Organizations(boto3)
        create_account_tags(
            event.get("account_id"),
            event.get("tags"),
            organizations,
        )
    else:
        LOGGER.info(
            f"Account: {event.get('account_full_name')} does not need tags configured"
        )
    return event
