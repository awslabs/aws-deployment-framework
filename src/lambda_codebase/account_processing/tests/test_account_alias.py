"""
Tests the account alias configuration lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from botocore.exceptions import ClientError
from mock import Mock
from aws_xray_sdk import global_sdk_config
from ..configure_account_alias import (
    create_account_alias,
    ensure_account_has_alias,
)

global_sdk_config.set_sdk_enabled(False)


class SuccessTestCase(unittest.TestCase):
    @staticmethod
    def test_account_alias_exists_already():
        test_account = {"account_id": 123456789012, "alias": "MyCoolAlias"}
        iam_client = Mock()
        iam_client.list_account_aliases.return_value = {
            "AccountAliases": ["MyCoolAlias"],
        }

        ensure_account_has_alias(test_account, iam_client)
        iam_client.list_account_aliases.assert_called_once_with()
        iam_client.delete_account_alias.assert_not_called()
        iam_client.create_account_alias.assert_not_called()

    @staticmethod
    def test_account_alias_another_alias_exists():
        test_account = {"account_id": 123456789012, "alias": "MyCoolAlias"}
        iam_client = Mock()
        iam_client.list_account_aliases.return_value = {
            "AccountAliases": ["AnotherCoolAlias"],
        }

        ensure_account_has_alias(test_account, iam_client)
        iam_client.list_account_aliases.assert_called_once_with()
        iam_client.delete_account_alias.assert_called_once_with(
            AccountAlias='AnotherCoolAlias',
        )
        iam_client.create_account_alias.assert_called_once_with(
            AccountAlias='MyCoolAlias',
        )

    @staticmethod
    def test_account_alias_no_aliases_yet():
        test_account = {"account_id": 123456789012, "alias": "MyCoolAlias"}
        iam_client = Mock()
        iam_client.list_account_aliases.return_value = {
            "AccountAliases": [],
        }

        ensure_account_has_alias(test_account, iam_client)
        iam_client.list_account_aliases.assert_called_once_with()
        iam_client.delete_account_alias.assert_not_called()
        iam_client.create_account_alias.assert_called_once_with(
            AccountAlias='MyCoolAlias',
        )


class FailureTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_account_alias_when_nonunique(self):
        test_account = {"account_id": 123456789012, "alias": "nonunique"}
        iam_client = boto3.client("iam")
        stubber = Stubber(iam_client)
        stubber.add_client_error(
            'create_account_alias',
            'EntityAlreadyExistsException',
            (
                "An error occurred (EntityAlreadyExists) when calling the "
                "CreateAccountAlias operation: The account alias "
                f"{test_account.get('alias')} already exists."
            ),
        )
        stubber.activate()

        with self.assertRaises(ClientError) as _error:
            create_account_alias(test_account, iam_client)
        self.assertRegex(
            str(_error.exception),
            r'.*The account alias nonunique already exists.*'
        )
