"""
Tests the account creation lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from aws_xray_sdk import global_sdk_config

from ..create_account import create_account

global_sdk_config.set_sdk_enabled(False)

# pylint: disable=W0106
class SuccessTestCase(unittest.TestCase):
    def test_account_creation(self):
        test_account = {
            "account_full_name": "ADF Test Creation Account",
            "email": "test@amazon.com",
        }
        test_account_result = {
            **test_account,
            "account_id": "111111111111",
        }
        org_client = boto3.client("organizations")
        stubber = Stubber(org_client)
        create_account_response = {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
                "Id": "1234567890",
            }
        }
        describe_account_response = {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
                "AccountId": "111111111111",
                "Id": "1234567890",
            }
        }
        describe_account_response_complete = {
            "CreateAccountStatus": {
                "State": "SUCCEEDED",
                "AccountId": "111111111111",
                "Id": "1234567890",
            }
        }
        stubber.add_response(
            "create_account",
            create_account_response,
            {
                "Email": test_account.get("email"),
                "AccountName": test_account.get("account_full_name"),
                "RoleName": "OrganizationAccountAccessRole",
                "IamUserAccessToBilling": "DENY",
            },
        ),
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response,
            {"CreateAccountRequestId": "1234567890"},
        )
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response_complete,
            {"CreateAccountRequestId": "1234567890"},
        )

        stubber.activate()

        response = create_account(
            test_account, "OrganizationAccountAccessRole", org_client
        )

        self.assertDictEqual(response, test_account_result)


class FailuteTestCase(unittest.TestCase):
    def test_account_creation_failure(self):
        test_account = {
            "account_full_name": "ADF Test Creation Account",
            "email": "test@amazon.com",
        }
        org_client = boto3.client("organizations")
        stubber = Stubber(org_client)
        create_account_response = {
            "CreateAccountStatus": {"State": "IN_PROGRESS", "Id": "1234567890"}
        }
        describe_account_response = {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
                "AccountId": "111111111111",
                "Id": "1234567890",
            }
        }
        describe_account_response_complete = {
            "CreateAccountStatus": {
                "State": "FAILED",
                "AccountId": "111111111111",
                "Id": "1234567890",
                "FailureReason": "ACCOUNT_LIMIT_EXCEEDED",
            }
        }
        stubber.add_response(
            "create_account",
            create_account_response,
            {
                "Email": test_account.get("email"),
                "AccountName": test_account.get("account_full_name"),
                "RoleName": "OrganizationAccountAccessRole",
                "IamUserAccessToBilling": "DENY",
            },
        ),
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response,
            {"CreateAccountRequestId": "1234567890"},
        )
        stubber.add_response(
            "describe_create_account_status",
            describe_account_response_complete,
            {"CreateAccountRequestId": "1234567890"},
        )

        stubber.activate()
        role = "OrganizationAccountAccessRole"

        with self.assertRaises(Exception):
            create_account(test_account, role, org_client)
