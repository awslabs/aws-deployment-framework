"""
Tests the account alias configuration lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from botocore.exceptions import ClientError
from aws_xray_sdk import global_sdk_config
from ..configure_account_alias import create_account_alias

global_sdk_config.set_sdk_enabled(False)

class SuccessTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_account_alias(self):
        test_account = {"account_id": 123456789012, "alias": "MyCoolAlias"}
        iam_client = boto3.client("iam")
        stubber = Stubber(iam_client)
        create_alias_response = {}
        stubber.add_response(
            "create_account_alias", create_alias_response, {"AccountAlias": "MyCoolAlias"}
        ),
        stubber.activate()

        response = create_account_alias(test_account, iam_client)

        self.assertEqual(response, test_account)

class FailureTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_account_alias_when_nonunique(self):
        test_account = {"account_id": 123456789012, "alias": "nonunique"}
        iam_client = boto3.client("iam")
        stubber = Stubber(iam_client)
        stubber.add_client_error(
            'create_account_alias',
            'EntityAlreadyExistsException',
            f"An error occurred (EntityAlreadyExists) when calling the CreateAccountAlias operation: The account alias {test_account.get('alias')} already exists."
        )
        stubber.activate()

        with self.assertRaises(ClientError) as _error:
            create_account_alias(test_account, iam_client)
        self.assertRegex(
            str(_error.exception),
            r'.*The account alias nonunique already exists.*'
        )
