"""
Tests the account alias configuration lambda
"""

import boto3
from botocore.stub import Stubber
from aws_xray_sdk import global_sdk_config
from ..configure_account_alias import create_account_alias

global_sdk_config.set_sdk_enabled(False)

# pylint: disable=W0106
def test_account_alias():
    test_account = {"account_id": 123456789012, "alias": "MyCoolAlias"}
    iam_client = boto3.client("iam")
    stubber = Stubber(iam_client)
    create_alias_response = {}
    stubber.add_response(
        "create_account_alias", create_alias_response, {"AccountAlias": "MyCoolAlias"}
    ),
    stubber.activate()

    response = create_account_alias(test_account, iam_client)

    assert response == test_account
