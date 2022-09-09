# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from datetime import datetime
import os
import boto3

from pytest import fixture
from stubs import stub_organizations
from mock import Mock, patch
from cache import Cache
from organizations import Organizations
from botocore.stub import Stubber
import unittest


@fixture
def cls():
    return Organizations(
        boto3,
        '123456789012'
    )


def test_get_parent_info(cls):
    cls.client = Mock()
    cls.client.list_parents.return_value = stub_organizations.list_parents
    assert cls.get_parent_info() == {
        "ou_parent_id": 'some_id',
        "ou_parent_type": 'ORGANIZATIONAL_UNIT'
    }


def test_get_organization_info(cls):
    cls.client = Mock()
    cls.client.describe_organization.return_value = stub_organizations.describe_organization
    assert cls.get_organization_info() == {
        'organization_id': 'some_org_id',
        'organization_master_account_id': 'some_master_account_id',
        'feature_set': 'ALL'
    }


def test_describe_ou_name(cls):
    cls.client = Mock()
    cls.client.describe_organizational_unit.return_value = stub_organizations.describe_organizational_unit
    assert cls.describe_ou_name('some_ou_id') == 'some_ou_name'


def test_describe_account_name(cls):
    cls.client = Mock()
    cls.client.describe_account.return_value = stub_organizations.describe_account
    assert cls.describe_account_name('some_account_id') == 'some_account_name'


def test_determine_ou_path(cls):
    assert cls.determine_ou_path(
        'some_path', 'some_ou_name'
    ) == 'some_path/some_ou_name'
    assert cls.determine_ou_path(
        'some_path/longer_path/plus_more',
        'some_ou_name'
    ) == 'some_path/longer_path/plus_more/some_ou_name'


def test_build_account_path(cls):
    cls.client = Mock()
    cache = Cache()
    cls.client.list_parents.return_value = stub_organizations.list_parents_root
    cls.client.describe_organizational_unit.return_value = stub_organizations.describe_organizational_unit

    assert cls.build_account_path('some_ou_id', [], cache) == 'some_ou_name'

class OUPathsHappyTestCases(unittest.TestCase):
    def test_nested_ou_paths(self):
        org_client = boto3.client("organizations")
        org_stubber = Stubber(org_client)
        tagging_client = boto3.client("organizations")
        tag_stubber = Stubber(tagging_client)

        list_roots_response = {
                "Roots": [
                    {
                        "Id": "r-1337",
                        "Arn": "arn:aws:organizations::root/r-1337",
                        "Name": "/",
                        "PolicyTypes": [],
                    }
                ]
        }

        list_organisational_units_for_root_response = {
            "OrganizationalUnits": [{
                "Id": "ou-123456",
                "Arn": "",
                "Name": "production"
            }]
        }

        list_organisational_units_for_production_response = {
            "OrganizationalUnits": [{
                "Id": "ou-080922",
                "Arn": "",
                "Name": "banking"
            }]
        }    

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9)
                }
            ],
            "NextToken": "PAGE1"
        }
        list_accounts_for_banking_response_page_1 = {
            "Accounts": [
                {
                    "Id": "22222222222",
                    "Arn": "",
                    "Email": "account+2@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9)
                }
            ]
        }

        expected_response = [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9)
                },            
                {
                    "Id": "22222222222",
                    "Arn": "",
                    "Email": "account+2@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9)
                }
            ]

        org_stubber.add_response("list_roots", list_roots_response)
        org_stubber.add_response("list_organizational_units_for_parent", list_organisational_units_for_root_response, {"ParentId": "r-1337"})
        org_stubber.add_response("list_organizational_units_for_parent", list_organisational_units_for_production_response, {"ParentId": "ou-123456"})
        org_stubber.add_response("list_accounts_for_parent", list_accounts_for_banking_response_page_0, {"ParentId": "ou-080922"})
        org_stubber.add_response("list_accounts_for_parent", list_accounts_for_banking_response_page_1, {"ParentId": "ou-080922", "NextToken": "PAGE1"})

        org_stubber.activate()
        tag_stubber.activate()
        organizations = Organizations(role=None, org_client=org_client, tagging_client=tagging_client)
        response = organizations.dir_to_ou("/production/banking")
        
        self.assertListEqual(expected_response, list(response))