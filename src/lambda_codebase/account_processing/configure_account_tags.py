# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates or adds tags to an account.
Currently only appends new tags.
Will not delete tags that aren't
in the config file.
"""


import json
import boto3

from organizations import Organizations
from aws_xray_sdk.core import patch_all
from logger import configure_logger
from events import ADFEvents

patch_all()
EVENTS = ADFEvents("AccountManagement")
LOGGER = configure_logger(__name__)


def create_account_tags(account_id, tags, org_session: Organizations):
    LOGGER.info(
        "Ensuring Account: %s has tags: %s",
        account_id,
        tags,
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
        EVENTS.put_event(
            detail=json.dumps(
                {"tags": event.get("tags"), "account_id": event.get("account_id")}
            ),
            detailType="ACCOUNT_TAGS_CONFIGURED",
            resources=[event.get("account_id")],
        )
    else:
        LOGGER.info(
            "Account: %s does not need tags configured",
            event.get("account_full_name"),
        )
    return event
