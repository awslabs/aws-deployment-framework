# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Creates or adds tags to an account.
Currently only appends new tags.
Will not delete tags that aren't
in the config file.
"""
import boto3
from aws_xray_sdk.core import patch_all
from logger import configure_logger

patch_all()
LOGGER = configure_logger(__name__)
ORG_CLIENT = boto3.client("organizations")


def create_account_tags(account_id, tags, client):
    LOGGER.info(
        "Ensuring Account: %s has tags: %s",
        account_id,
        tags,
    )
    formatted_tags = [
        {"Key": str(key), "Value": str(value)}
        for tag in tags
        for key, value in tag.items()
    ]
    LOGGER.debug(
        "Ensuring Account: %s has tags (formatted): %s",
        account_id,
        formatted_tags,
    )
    client.tag_resource(ResourceId=account_id, Tags=formatted_tags)


def lambda_handler(event, _):
    if event.get("tags"):
        create_account_tags(
            event.get("account_id"),
            event.get("tags"),
            ORG_CLIENT,
        )
    else:
        LOGGER.info(
            "Account: %s does not need tags configured",
            event.get("account_full_name"),
        )
    return event
