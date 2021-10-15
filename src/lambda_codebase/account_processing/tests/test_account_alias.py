"""
Tests the account alias configuration lambda
"""

import boto3
from botocore.stub import Stubber

from ..configure_account_alias import create_account_alias

# pylint: disable=W0106
def test_account_alias():
    test_account = {"Id": 1234567890, "alias": "MyCoolAlias"}
    iam_client = boto3.client("iam")
    stubber = Stubber(iam_client)
    create_alias_response = {}
    stubber.add_response(
        "create_account_alias", create_alias_response, {"AccountAlias": "MyCoolAlias"}
    ),
    stubber.activate()
    response = create_account_alias(test_account, iam_client)
    assert response == test_account
