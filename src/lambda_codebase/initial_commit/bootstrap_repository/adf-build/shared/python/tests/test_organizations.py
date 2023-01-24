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
from organizations import Organizations, OrganizationsException
from botocore.stub import Stubber
import unittest


@fixture
def cls():
    return Organizations(boto3, "123456789012")


def test_get_parent_info(cls):
    cls.client = Mock()
    cls.client.list_parents.return_value = stub_organizations.list_parents
    assert cls.get_parent_info() == {
        "ou_parent_id": "some_id",
        "ou_parent_type": "ORGANIZATIONAL_UNIT",
    }
    cls.client.list_parents.assert_called_once_with(
        ChildId=cls.account_id,
    )


def test_get_parent_info_specific_account(cls):
    specific_account_id = "111111111111"
    cls.client = Mock()
    cls.client.list_parents.return_value = stub_organizations.list_parents
    assert cls.get_parent_info(specific_account_id) == {
        "ou_parent_id": "some_id",
        "ou_parent_type": "ORGANIZATIONAL_UNIT",
    }
    cls.client.list_parents.assert_called_once_with(
        ChildId=specific_account_id,
    )


@patch("organizations.paginator")
def test_get_accounts(paginator_mock, cls):
    all_account_ids = [
        "111111111111",
        "222222222222",
        "333333333333",
        "444444444444",
    ]
    root_account_ids = [
        "333333333333",
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda account_id: (
        {
            "Id": (
                f"r-{account_id}"
                if account_id in root_account_ids
                else f"ou-{account_id}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }
    )
    paginator_mock.return_value = list(
        map(
            lambda account_id: (
                {
                    "Id": account_id,
                    "Status": "ACTIVE",
                }
            ),
            all_account_ids,
        )
    )
    assert set(
        map(
            lambda account: account["Id"],
            cls.get_accounts(),
        )
    ) == set(all_account_ids)


@patch("organizations.paginator")
def test_get_accounts_with_suspended(paginator_mock, cls):
    all_account_ids = [
        "111111111111",
        "222222222222",
        "333333333333",
        "444444444444",
    ]
    root_account_ids = [
        "333333333333",
    ]
    suspended_account_ids = [
        "444444444444",
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda account_id: (
        {
            "Id": (
                f"r-{account_id}"
                if account_id in root_account_ids
                else f"ou-{account_id}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }
    )
    paginator_mock.return_value = list(
        map(
            lambda account_id: (
                {
                    "Id": account_id,
                    "Status": (
                        "SUSPENDED" if account_id in suspended_account_ids else "ACTIVE"
                    ),
                }
            ),
            all_account_ids,
        )
    )
    assert set(
        map(
            lambda account: account["Id"],
            cls.get_accounts(),
        )
    ) == (set(all_account_ids) - set(suspended_account_ids))


@patch("organizations.paginator")
def test_get_accounts_ignore_root(paginator_mock, cls):
    all_account_ids = [
        "111111111111",
        "222222222222",
        "333333333333",
        "444444444444",
    ]
    root_account_ids = [
        "444444444444",
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: (
        {
            "Parents": [
                {
                    "Id": (
                        f"r-{ChildId}"
                        if ChildId in root_account_ids
                        else f"ou-{ChildId}"
                    ),
                    "Type": "ORGANIZATIONAL_UNIT",
                }
            ],
        }
    )
    paginator_mock.return_value = list(
        map(
            lambda account_id: (
                {
                    "Id": account_id,
                    "Status": "ACTIVE",
                }
            ),
            all_account_ids,
        )
    )
    assert set(
        map(
            lambda account: account["Id"],
            cls.get_accounts(
                include_root=False,
            ),
        )
    ) == (set(all_account_ids) - set(root_account_ids))


@patch("organizations.paginator")
def test_get_accounts_ignore_protected(paginator_mock, cls):
    all_account_ids = [
        "111111111111",
        "222222222222",
        "333333333333",
        "444444444444",
    ]
    root_account_ids = [
        "444444444444",
    ]
    protected_account_ids = [
        "222222222222",
    ]
    protected_ou_ids = list(
        map(
            lambda account_id: f"ou-{account_id}",
            protected_account_ids,
        )
    )
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: (
        {
            "Parents": [
                {
                    "Id": (
                        f"r-{ChildId}"
                        if ChildId in root_account_ids
                        else f"ou-{ChildId}"
                    ),
                    "Type": "ORGANIZATIONAL_UNIT",
                }
            ],
        }
    )
    paginator_mock.return_value = list(
        map(
            lambda account_id: (
                {
                    "Id": account_id,
                    "Status": "ACTIVE",
                }
            ),
            all_account_ids,
        )
    )
    assert set(
        map(
            lambda account: account["Id"],
            cls.get_accounts(
                protected_ou_ids=protected_ou_ids,
            ),
        )
    ) == (set(all_account_ids) - set(protected_account_ids))


@patch("organizations.paginator")
def test_get_accounts_ignore_root_protected_and_inactive(paginator_mock, cls):
    all_account_ids = [
        "111111111111",
        "222222222222",
        "333333333333",
        "444444444444",
        "555555555555",
        "666666666666",
        "777777777777",
        "888888888888",
    ]
    protected_account_ids = [
        "222222222222",
        "777777777777",
    ]
    root_account_ids = [
        "333333333333",
        "888888888888",
    ]
    suspended_account_ids = [
        "444444444444",
    ]
    pending_closure_account_ids = [
        "555555555555",
    ]
    protected_ou_ids = list(
        map(
            lambda account_id: f"ou-{account_id}",
            protected_account_ids,
        )
    )
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: (
        {
            "Parents": [
                {
                    "Id": (
                        f"r-{ChildId}"
                        if ChildId in root_account_ids
                        else f"ou-{ChildId}"
                    ),
                    "Type": "ORGANIZATIONAL_UNIT",
                }
            ],
        }
    )
    paginator_mock.return_value = list(
        map(
            lambda account_id: (
                {
                    "Id": account_id,
                    "Status": (
                        "SUSPENDED"
                        if account_id in suspended_account_ids
                        else (
                            "PENDING_CLOSURE"
                            if account_id in pending_closure_account_ids
                            else "ACTIVE"
                        )
                    ),
                }
            ),
            all_account_ids,
        )
    )
    assert set(
        map(
            lambda account: account["Id"],
            cls.get_accounts(
                protected_ou_ids=protected_ou_ids,
                include_root=False,
            ),
        )
    ) == (
        set(all_account_ids)
        - set(protected_account_ids)
        - set(root_account_ids)
        - set(suspended_account_ids)
        - set(pending_closure_account_ids)
    )


def test_get_organization_info(cls):
    cls.client = Mock()
    cls.client.describe_organization.return_value = (
        stub_organizations.describe_organization
    )
    assert cls.get_organization_info() == {
        "organization_id": "some_org_id",
        "organization_master_account_id": "some_master_account_id",
        "feature_set": "ALL",
    }


def test_describe_ou_name(cls):
    cls.client = Mock()
    cls.client.describe_organizational_unit.return_value = (
        stub_organizations.describe_organizational_unit
    )
    assert cls.describe_ou_name("some_ou_id") == "some_ou_name"


def test_describe_account_name(cls):
    cls.client = Mock()
    cls.client.describe_account.return_value = stub_organizations.describe_account
    assert cls.describe_account_name("some_account_id") == "some_account_name"


def test_determine_ou_path(cls):
    assert (
        cls.determine_ou_path("some_path", "some_ou_name") == "some_path/some_ou_name"
    )
    assert (
        cls.determine_ou_path("some_path/longer_path/plus_more", "some_ou_name")
        == "some_path/longer_path/plus_more/some_ou_name"
    )


def test_build_account_path(cls):
    cls.client = Mock()
    cache = Cache()
    cls.client.list_parents.return_value = stub_organizations.list_parents_root
    cls.client.describe_organizational_unit.return_value = (
        stub_organizations.describe_organizational_unit
    )
    assert cls.build_account_path("some_ou_id", [], cache) == "some_ou_name"


class OUPathsHappyTestCases(unittest.TestCase):
    """
    These test cases all use the same org structure
    /production
    No Accounts
    /production/banking
    Accounts: 111111111, 22222222
    /production/banking/investment
    Accounts: 333333333

    """

    def test_original_ou_paths(self):
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

        list_organizational_units_for_root_response = {
            "OrganizationalUnits": [
                {"Id": "ou-123456", "Arn": "", "Name": "production"}
            ]
        }

        list_organizational_units_for_production_response = {
            "OrganizationalUnits": [{"Id": "ou-080922", "Arn": "", "Name": "banking"}]
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"}
            ]
        }

        list_organizational_units_for_investment_response = {"OrganizationalUnits": []}

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ],
            "NextToken": "PAGE1",
        }
        list_accounts_for_banking_response_page_1 = {
            "Accounts": [
                {
                    "Id": "22222222222",
                    "Arn": "",
                    "Email": "account+2@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ]
        }

        list_accounts_for_investment_response_page_0 = {
            "Accounts": [
                {
                    "Id": "3333333333",
                    "Arn": "",
                    "Email": "account+3@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
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
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
        ]

        org_stubber.add_response("list_roots", list_roots_response)
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_root_response,
            {"ParentId": "r-1337"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_production_response,
            {"ParentId": "ou-123456"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_0,
            {"ParentId": "ou-080922"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_1,
            {"ParentId": "ou-080922", "NextToken": "PAGE1"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_banking_response,
            {"ParentId": "ou-080922"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_investment_response_page_0,
            {"ParentId": "ou-09092022"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_investment_response,
            {"ParentId": "ou-09092022"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_investment_response_page_0,
            {"ParentId": "ou-09092022"},
        )

        org_stubber.activate()
        tag_stubber.activate()
        organizations = Organizations(
            role=None, org_client=org_client, tagging_client=tagging_client
        )
        response = organizations.dir_to_ou("/production/banking")

        self.assertListEqual(expected_response, list(response))

    def test_original_nested_paths(self):
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

        list_organizational_units_for_root_response = {
            "OrganizationalUnits": [
                {"Id": "ou-123456", "Arn": "", "Name": "production"}
            ]
        }

        list_organizational_units_for_production_response = {
            "OrganizationalUnits": [{"Id": "ou-080922", "Arn": "", "Name": "banking"}]
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"}
            ]
        }

        list_organizational_units_for_investment_response = {"OrganizationalUnits": []}

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ],
            "NextToken": "PAGE1",
        }
        list_accounts_for_banking_response_page_1 = {
            "Accounts": [
                {
                    "Id": "22222222222",
                    "Arn": "",
                    "Email": "account+2@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ]
        }

        list_accounts_for_investment_response_page_0 = {
            "Accounts": [
                {
                    "Id": "3333333333",
                    "Arn": "",
                    "Email": "account+3@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
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
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
            {
                "Id": "3333333333",
                "Arn": "",
                "Email": "account+3@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
        ]

        org_stubber.add_response("list_roots", list_roots_response)
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_root_response,
            {"ParentId": "r-1337"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_production_response,
            {"ParentId": "ou-123456"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_0,
            {"ParentId": "ou-080922"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_1,
            {"ParentId": "ou-080922", "NextToken": "PAGE1"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_banking_response,
            {"ParentId": "ou-080922"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_investment_response_page_0,
            {"ParentId": "ou-09092022"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_investment_response,
            {"ParentId": "ou-09092022"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_investment_response_page_0,
            {"ParentId": "ou-09092022"},
        )

        org_stubber.activate()
        tag_stubber.activate()
        organizations = Organizations(
            role=None, org_client=org_client, tagging_client=tagging_client
        )
        response = organizations.get_accounts_in_path(
            "/production/banking", resolve_children=True
        )

        self.assertListEqual(expected_response, list(response))

    def test_nested_paths_with_exclusions(self):
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

        list_organizational_units_for_root_response = {
            "OrganizationalUnits": [
                {"Id": "ou-123456", "Arn": "", "Name": "production"}
            ]
        }

        list_organizational_units_for_production_response = {
            "OrganizationalUnits": [{"Id": "ou-080922", "Arn": "", "Name": "banking"}]
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"},
                {"Id": "ou-26092022", "Arn": "", "Name": "commercial"},
            ]
        }

        list_organizational_units_for_investment_response = {"OrganizationalUnits": []}

        list_organizational_units_for_commercial_response = {"OrganizationalUnits": []}

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ],
            "NextToken": "PAGE1",
        }
        list_accounts_for_banking_response_page_1 = {
            "Accounts": [
                {
                    "Id": "22222222222",
                    "Arn": "",
                    "Email": "account+2@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ]
        }

        list_accounts_for_investment_response_page_0 = {
            "Accounts": [
                {
                    "Id": "3333333333",
                    "Arn": "",
                    "Email": "account+3@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 8, 9),
                }
            ]
        }

        list_accounts_for_commercial_response_page_0 = {
            "Accounts": [
                {
                    "Id": "444444444",
                    "Arn": "",
                    "Email": "account+4@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": datetime(2022, 9, 26),
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
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": datetime(2022, 8, 9),
            },
            {
                "Id": "444444444",
                "Arn": "",
                "Email": "account+4@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": datetime(2022, 9, 26),
            },
        ]

        org_stubber.add_response("list_roots", list_roots_response)
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_root_response,
            {"ParentId": "r-1337"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_production_response,
            {"ParentId": "ou-123456"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_0,
            {"ParentId": "ou-080922"},
        )
        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_banking_response_page_1,
            {"ParentId": "ou-080922", "NextToken": "PAGE1"},
        )
        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_banking_response,
            {"ParentId": "ou-080922"},
        )

        org_stubber.add_response(
            "list_accounts_for_parent",
            list_accounts_for_commercial_response_page_0,
            {"ParentId": "ou-26092022"},
        )

        org_stubber.add_response(
            "list_organizational_units_for_parent",
            list_organizational_units_for_commercial_response,
            {"ParentId": "ou-26092022"},
        )

        org_stubber.activate()
        tag_stubber.activate()
        organizations = Organizations(
            role=None, org_client=org_client, tagging_client=tagging_client
        )
        response = organizations.get_accounts_in_path(
            "/production/banking",
            resolve_children=True,
            excluded_paths=["/production/banking/investment"],
        )

        self.assertListEqual(expected_response, list(response))


class OrgClientInitTestCases(unittest.TestCase):
    def test_init(self):
        with self.assertRaises(OrganizationsException) as context:
            Organizations()
        assert Organizations(role=boto3)
