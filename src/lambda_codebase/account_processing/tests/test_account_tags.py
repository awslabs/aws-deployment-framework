"""
Tests the account tag configuration lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from aws_xray_sdk import global_sdk_config
from ..configure_account_tags import (
    create_account_tags,
)

global_sdk_config.set_sdk_enabled(False)

# pylint: disable=W0106
class SuccessTestCase(unittest.TestCase):
    @staticmethod
    def test_account_tag_creation():
        test_event = {"account_id": "123456789012", "tags": [{"CreatedBy": "ADF"}]}
        ou_client = boto3.client("organizations")
        stubber = Stubber(ou_client)
        stubber.add_response(
            "tag_resource",
            {},
            {
                "Tags": [{"Key": "CreatedBy", "Value": "ADF"}],
                "ResourceId": "123456789012",
            },
        ),
        stubber.activate()
        create_account_tags(
            test_event.get("account_id"), test_event.get("tags"), ou_client
        )
