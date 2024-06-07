# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Creates or updates an ALIAS for an account
"""

import os

from aws_xray_sdk.core import patch_all

# ADF imports
from logger import configure_logger
from sts import STS

patch_all()

LOGGER = configure_logger(__name__)
ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME = os.getenv("ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME")
AWS_PARTITION = os.getenv("AWS_PARTITION")
MANAGEMENT_ACCOUNT_ID = os.getenv('MANAGEMENT_ACCOUNT_ID')


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
            "The account alias %s already exists."
            "The account alias must be unique across all Amazon Web Services "
            "products. Refer to "
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/"
            "console_account-alias.html#AboutAccountAlias",
            account.get('alias'),
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
        role = sts.assume_bootstrap_deployment_role(
            AWS_PARTITION,
            MANAGEMENT_ACCOUNT_ID,
            account_id,
            ADF_PRIVILEGED_CROSS_ACCOUNT_ROLE_NAME,
            "adf_account_alias_config",
        )
        ensure_account_has_alias(event, role.client("iam"))
    else:
        LOGGER.info(
            "Account: %s does not need an alias",
            event.get('account_full_name'),
        )
    return event
