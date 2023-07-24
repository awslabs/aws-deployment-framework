"""
Tests the account tag configuration lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from aws_xray_sdk import global_sdk_config
from ..get_account_regions import (
    get_default_regions_for_account,
)

global_sdk_config.set_sdk_enabled(False)

# pylint: disable=W0106
class SuccessTestCase(unittest.TestCase):
    @staticmethod
    def test_get_default_regions_for_account():
        ec2_client = boto3.client("ec2")
        stubber = Stubber(ec2_client)
        stubber.add_response(
            "describe_regions",
            {
                "Regions": [
                    {
                        "Endpoint": "blah",
                        "RegionName": "us-east-1",
                        "OptInStatus": "opt-in-not-required",
                    },
                    {
                        "Endpoint": "blah",
                        "RegionName": "us-east-2",
                        "OptInStatus": "opt-in-not-required",
                    },
                    {
                        "Endpoint": "blah",
                        "RegionName": "us-east-3",
                        "OptInStatus": "opted-in",
                    },
                    {
                        "Endpoint": "blah",
                        "RegionName": "us-east-4",
                        "OptInStatus": "opted-in",
                    },
                ]
            },
            {
                "AllRegions": False,
                "Filters": [
                    {
                        "Values": [
                            "opt-in-not-required",
                            "opted-in",
                        ],
                        "Name": "opt-in-status",
                    },
                ],
            },
        ),
        stubber.activate()
        regions = get_default_regions_for_account(ec2_client)
        assert regions == ["us-east-1", "us-east-2", "us-east-3", "us-east-4"]
