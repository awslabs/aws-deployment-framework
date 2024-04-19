# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Tests the account alias configuration lambda
"""

import unittest
import boto3
from botocore.stub import Stubber
from aws_xray_sdk import global_sdk_config
from ..configure_account_regions import get_regions_from_ssm, enable_regions_for_account

global_sdk_config.set_sdk_enabled(False)


class SuccessTestCase(unittest.TestCase):
    def test_get_regions_from_ssm(self):
        ssm_client = boto3.client("ssm", region_name="us-east-1")
        ssm_stubber = Stubber(ssm_client)
        ssm_stubber.add_response("get_parameter", {"Parameter": {"Value": "[1,2,3]"}})
        ssm_stubber.activate()
        self.assertListEqual(get_regions_from_ssm(ssm_client), [1, 2, 3])

    def test_enable_regions_for_account(self):
        accounts_client = boto3.client("account", region_name="us-east-1")
        account_stubber = Stubber(accounts_client)
        account_stubber.add_response(
            "list_regions",
            {
                "Regions": [
                    {"RegionName": "us-east-1", "RegionOptStatus": "ENABLED_BY_DEFAULT"}
                ]
            },
        )
        account_stubber.activate()
        self.assertTrue(
            enable_regions_for_account(
                accounts_client,
                "123456789",
                desired_regions=["us-east-1"],
                org_root_account_id="123456789",
            )
        )

    def test_enable_regions_for_account_with_pagination(self):
        accounts_client = boto3.client("account", region_name="us-east-1")
        account_stubber = Stubber(accounts_client)
        account_stubber.add_response(
            "list_regions",
            {
                "Regions": [
                    {"RegionName": "us-east-1", "RegionOptStatus": "ENABLED_BY_DEFAULT"}
                ],
                "NextToken": "1",
            },
        )
        account_stubber.add_response(
            "list_regions",
            {
                "Regions": [
                    {"RegionName": "af-south-1", "RegionOptStatus": "DISABLED"}
                ],
                "NextToken": "2",
            },
        )
        account_stubber.add_response(
            "list_regions",
            {"Regions": [{"RegionName": "sco-west-1", "RegionOptStatus": "DISABLED"}]},
        )
        account_stubber.add_response(
            "enable_region",
            {},
            {"RegionName": "af-south-1"},
        )
        account_stubber.add_response(
            "enable_region",
            {},
            {"RegionName": "sco-west-1"},
        )
        account_stubber.activate()
        self.assertFalse(
            enable_regions_for_account(
                accounts_client,
                "123456789",
                desired_regions=["us-east-1", "af-south-1", "sco-west-1"],
                org_root_account_id="123456789",
            )
        )
        account_stubber.assert_no_pending_responses()

    def test_enable_regions_for_account_that_is_not_current_account(self):
        accounts_client = boto3.client("account", region_name="us-east-1")
        account_stubber = Stubber(accounts_client)
        account_stubber.add_response(
            "list_regions",
            {
                "Regions": [
                    {
                        "RegionName": "us-east-1",
                        "RegionOptStatus": "ENABLED_BY_DEFAULT",
                    },
                    {"RegionName": "sco-west-1", "RegionOptStatus": "DISABLED"},
                ]
            },
        )
        account_stubber.add_response(
            "enable_region",
            {},
            {
                "RegionName": "sco-west-1",
                "AccountId": "123456789",
            },
        )
        account_stubber.activate()
        self.assertFalse(
            enable_regions_for_account(
                accounts_client,
                "123456789",
                desired_regions=["us-east-1", "sco-west-1"],
                org_root_account_id="987654321",
            )
        )
