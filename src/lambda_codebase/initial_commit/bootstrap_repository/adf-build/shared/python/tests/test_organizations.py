# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from datetime import datetime, timezone
import os
import boto3

from pytest import fixture, raises
from stubs import stub_organizations
from mock import Mock, patch
from cache import Cache
from organizations import Organizations, OrganizationsException
from botocore.stub import Stubber
from botocore.exceptions import ClientError
import unittest


@fixture
def cache():
    return Cache()


@fixture
def org_client():
    return Mock()


@fixture
def tagging_client():
    return Mock()


@fixture
def cls(org_client, tagging_client, cache):
    return Organizations(
        account_id="123456789012",
        org_client=org_client,
        tagging_client=tagging_client,
        cache=cache
    )


def test_has_cache():
    orgs = Organizations(boto3, "123456789012")
    assert orgs.cache is not None


def test_has_supplied_cache(cls, cache):
    assert cls.cache == cache


def test_create_ou(cls):
    cls.client = Mock()
    cls.client.create_organizational_unit.return_value = stub_organizations.create_organizational_unit

    ou = cls.create_ou("some_parent_id", "some_ou_name")

    assert ou['OrganizationalUnit']["Id"] == "new_ou_id"
    assert ou['OrganizationalUnit']["Name"] == "new_ou_name"

def test_create_ou_throws_client_error(cls):
    cls.client = Mock()
    cls.client.create_organizational_unit.side_effect = ClientError(operation_name='test', error_response={'Error': {'Code': 'Test', 'Message': 'Test Message'}})
    with raises(OrganizationsException): 
        cls.create_ou("some_parent_id", "some_ou_name")


def test_get_ou_id_can_create_ou_one_layer(cls):
    cls.client = Mock()
    cls.client.create_organizational_unit.return_value = stub_organizations.create_organizational_unit
    cls.client.get_paginator("list_organizational_units_for_parent").paginate.return_value = stub_organizations.list_organizational_units_for_parent

    ou_id = cls.get_ou_id("/existing/new")

    assert ou_id == "new_ou_id"


def test_get_parent_info(cls):
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
                        "SUSPENDED" if account_id in suspended_account_ids
                        else "ACTIVE"
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


def test_get_organization_info(cls, cache):
    # Arrange
    assert cache.exists("organization") is False
    cls.client.describe_organization.return_value = (
        stub_organizations.describe_organization
    )

    # Act
    result = cls.get_organization_info()

    # Assert
    assert result == {
        "organization_id": "some_org_id",
        "organization_management_account_id": "some_management_account_id",
        "feature_set": "ALL",
    }
    cls.client.describe_organization.assert_called_once_with()
    assert cache.exists("organization") is True
    assert cache.get("organization") == stub_organizations.describe_organization


def test_get_organization_info_cached(cls, cache):
    # Arrange
    cache.add("organization", stub_organizations.describe_organization)

    # Act
    result = cls.get_organization_info()

    # Assert
    assert result == {
        "organization_id": "some_org_id",
        "organization_management_account_id": "some_management_account_id",
        "feature_set": "ALL",
    }
    cls.client.describe_organization.assert_not_called()


def test_describe_ou_name(cls, cache):
    # Arrange
    ou_id = "some_ou_id"
    expected_ou_name = "some_ou_name"
    cache_id = f"ou_name_{ou_id}"
    assert cache.exists(cache_id) is False
    cls.client.describe_organizational_unit.return_value = (
        stub_organizations.describe_organizational_unit
    )

    # Act
    result = cls.describe_ou_name(ou_id)

    # Assert
    assert result == expected_ou_name
    cls.client.describe_organizational_unit.assert_called_once_with(
        OrganizationalUnitId=ou_id,
    )
    assert cache.exists(cache_id) is True
    assert cache.get(cache_id) == expected_ou_name


def test_describe_ou_name_cached(cls, cache):
    # Arrange
    ou_id = "some_ou_id"
    expected_ou_name = "some_ou_name"
    cache.add(f"ou_name_{ou_id}", expected_ou_name)

    # Act
    result = cls.describe_ou_name(ou_id)

    # Assert
    assert result == expected_ou_name
    cls.client.describe_organizational_unit.assert_not_called()


def test_describe_account_name(cls, cache):
    # Arrange
    account_id = "111111111111"
    expected_account_name = "some_account_name"
    cache_id = f"account_name_{account_id}"
    cls.client.describe_account.return_value = (
        stub_organizations.describe_account
    )

    # Act
    result = cls.describe_account_name(account_id)

    # Assert
    assert result == expected_account_name
    cls.client.describe_account.assert_called_once_with(AccountId=account_id)
    assert cache.exists(cache_id) is True
    assert cache.get(cache_id) == expected_account_name


def test_describe_account_name_cached(cls, cache):
    # Arrange
    account_id = "111111111111"
    expected_account_name = "some_account_name"
    cache.add(f"account_name_{account_id}", expected_account_name)

    # Act
    result = cls.describe_account_name(account_id)

    # Assert
    assert result == expected_account_name
    cls.client.describe_account.assert_not_called()


def test_determine_ou_path(cls):
    assert cls.determine_ou_path("some_path", "some_ou_name") == (
        "some_path/some_ou_name"
    )
    assert (
        cls.determine_ou_path(
            "some_path/longer_path/plus_more",
            "some_ou_name",
        )
        == "some_path/longer_path/plus_more/some_ou_name"
    )


def test_list_parents(cls, cache):
    # Arrange
    ou_id = "ou-1234"
    expected_parent = {"Id": "ou-5678", "Type": "ORGANIZATIONAL_UNIT"}
    cache_id = f"parents_{ou_id}"
    cls.client.list_parents.return_value = {"Parents": [expected_parent]}

    # Act
    result = cls.list_parents(ou_id)

    # Assert
    assert result == expected_parent
    cls.client.list_parents.assert_called_once_with(ChildId=ou_id)
    assert cache.exists(cache_id) is True
    assert cache.get(cache_id) == expected_parent


def test_list_parents_cached(cls, cache):
    # Arrange
    ou_id = "ou-1234"
    expected_parent = {"Id": "ou-5678", "Type": "ORGANIZATIONAL_UNIT"}
    cache.add(f"parents_{ou_id}", expected_parent)

    # Act
    result = cls.list_parents(ou_id)

    # Assert
    assert result == expected_parent
    cls.client.list_parents.assert_not_called()


def test_get_ou_root_id(cls, cache):
    # Arrange
    expected_id = "r-1234"
    cls.client.list_roots.return_value = {"Roots": [{"Id": expected_id}]}

    # Act
    result = cls.get_ou_root_id()

    # Assert
    assert result == expected_id
    cls.client.list_roots.assert_called_once()
    assert cache.exists('root_id') is True
    assert cache.get('root_id') == expected_id


def test_get_ou_root_id_cached(cls, cache):
    # Arrange
    expected_id = "r-1234"
    cache.add('root_id', expected_id)

    # Act
    result = cls.get_ou_root_id()

    # Assert
    assert result == expected_id
    cls.client.list_roots.assert_not_called()


def test_build_account_path_first_level(cls, cache):
    """Test building account path with first level of OUs"""
    # Arrange
    ou_id = "ou-child"

    cls.client.list_parents.side_effect = [
        # Call for parent:
        {"Parents": [{"Id": "r-1234", "Type": "ROOT"}]},
        # Call for account:
        {"Parents": [{"Id": "r-1234", "Type": "ROOT"}]},
    ]

    cls.client.describe_organizational_unit.side_effect = [
        {"OrganizationalUnit": {"Name": "WebApps"}},  # Parent OU
    ]

    # Act
    path_ids = []
    result = cls.build_account_path(ou_id, path_ids)

    # Assert
    assert result == "WebApps"
    assert path_ids == []


def test_build_account_path_second_level(cls, cache):
    """Test building account path with two levels of OUs"""
    # Arrange
    ou_id = "ou-child"
    parent_ou_id = "ou-parent"

    list_parent_responses = {
        cls.account_id: {"Parents": [{"Id": ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        ou_id: {"Parents": [{"Id": parent_ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        parent_ou_id: {"Parents": [{"Id": "r-1234", "Type": "ROOT"}]},
    }
    cls.client.list_parents.side_effect = lambda **kwargs: list_parent_responses.get(
        kwargs['ChildId'],
    )

    describe_ou_responses = {
        cls.account_id: {"OrganizationalUnit": {"Name": "Development"}},
        ou_id: {"OrganizationalUnit": {"Name": "Development"}},
        parent_ou_id: {"OrganizationalUnit": {"Name": "WebApps"}},
    }
    cls.client.describe_organizational_unit.side_effect = lambda **kwargs: describe_ou_responses.get(
        kwargs['OrganizationalUnitId'],
    )

    # Act
    path_ids = []
    result = cls.build_account_path(ou_id, path_ids)

    # Assert
    assert result == "WebApps/Development"
    assert path_ids == ['WebApps']


def test_build_account_path_fourth_level(cls, cache):
    """Test building account path with four levels of OUs"""
    # Arrange
    ou_id = "ou-child"
    parent_ou_id = "ou-parent"
    grandparent_ou_id = "ou-grandparent"
    great_grandparent_ou_id = "ou-great-grandparent"

    list_parent_responses = {
        cls.account_id: {"Parents": [{"Id": ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        ou_id: {"Parents": [{"Id": parent_ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        parent_ou_id: {"Parents": [{"Id": grandparent_ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        grandparent_ou_id: {"Parents": [{"Id": great_grandparent_ou_id, "Type": "ORGANIZATIONAL_UNIT"}]},
        great_grandparent_ou_id: {"Parents": [{"Id": "r-1234", "Type": "ROOT"}]},
    }
    cls.client.list_parents.side_effect = lambda **kwargs: list_parent_responses.get(
        kwargs['ChildId'],
    )

    describe_ou_responses = {
        cls.account_id: {"OrganizationalUnit": {"Name": "eu-west-1"}},
        ou_id: {"OrganizationalUnit": {"Name": "eu-west-1"}},
        parent_ou_id: {"OrganizationalUnit": {"Name": "App1"}},
        grandparent_ou_id: {"OrganizationalUnit": {"Name": "Development"}},
        great_grandparent_ou_id: {"OrganizationalUnit": {"Name": "WebApps"}},
    }
    cls.client.describe_organizational_unit.side_effect = lambda **kwargs: describe_ou_responses.get(
        kwargs['OrganizationalUnitId'],
    )

    # Act
    path_ids = []
    result = cls.build_account_path(ou_id, path_ids)

    # Assert
    assert result == "WebApps/Development/App1/eu-west-1"
    assert path_ids == ['App1', 'Development', 'WebApps']


def test_list_organizational_units_for_parent_single_page(cls, cache):
    """Test listing OUs for parent with single page response"""
    # Arrange
    parent_id = "ou-1234"
    expected_ous = [
        {"Id": "ou-5678", "Name": "Development"},
        {"Id": "ou-9012", "Name": "Production"}
    ]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"OrganizationalUnits": expected_ous}]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_organizational_units_for_parent(parent_id)

    # Assert
    assert result == expected_ous
    assert cache.get(f'children_{parent_id}') == expected_ous
    cls.client.get_paginator.assert_called_once_with('list_organizational_units_for_parent')
    paginator_mock.paginate.assert_called_once_with(ParentId=parent_id)


def test_list_organizational_units_for_parent_cached(cls, cache):
    """Test listing OUs when results are already in cache"""
    # Arrange
    parent_id = "ou-1234"
    cached_ous = [
        {"Id": "ou-5678", "Name": "Development"},
        {"Id": "ou-9012", "Name": "Production"}
    ]
    cache.add(f'children_{parent_id}', cached_ous)

    # Act
    result = cls.list_organizational_units_for_parent(parent_id)

    # Assert
    assert result == cached_ous
    cls.client.get_paginator.assert_not_called()


def test_list_organizational_units_for_parent_multiple_pages(cls, cache):
    """Test listing OUs with paginated results"""
    # Arrange
    parent_id = "ou-1234"
    page1_ous = [{"Id": "ou-5678", "Name": "Development"}]
    page2_ous = [{"Id": "ou-9012", "Name": "Production"}]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [
        {"OrganizationalUnits": page1_ous},
        {"OrganizationalUnits": page2_ous}
    ]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_organizational_units_for_parent(parent_id)

    # Assert
    assert result == page1_ous + page2_ous
    assert cache.get(f'children_{parent_id}') == page1_ous + page2_ous
    paginator_mock.paginate.assert_called_once_with(ParentId=parent_id)


def test_list_organizational_units_for_parent_empty(cls, cache):
    """Test listing OUs when parent has no children"""
    # Arrange
    parent_id = "ou-1234"
    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"OrganizationalUnits": []}]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_organizational_units_for_parent(parent_id)

    # Assert
    assert result == []
    assert cache.get(f'children_{parent_id}') == []
    paginator_mock.paginate.assert_called_once_with(ParentId=parent_id)


def test_list_organizational_units_for_parent_different_parents(cls, cache):
    """Test listing OUs for different parents"""
    # Arrange
    parent_map = {
        "ou-parent1": [{"Id": "ou-child1", "Name": "Development"}],
        "ou-parent2": [{"Id": "ou-child2", "Name": "Production"}]
    }

    paginator_mock = Mock()
    paginator_mock.paginate.side_effect = lambda **kwargs: [
        {"OrganizationalUnits": parent_map.get(kwargs['ParentId'], [])}
    ]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result1 = cls.list_organizational_units_for_parent("ou-parent1")
    result2 = cls.list_organizational_units_for_parent("ou-parent2")

    # Assert
    assert result1 == parent_map["ou-parent1"]
    assert result2 == parent_map["ou-parent2"]
    assert cache.get('children_ou-parent1') == parent_map["ou-parent1"]
    assert cache.get('children_ou-parent2') == parent_map["ou-parent2"]


def test_list_organizational_units_for_parent_root(cls, cache):
    """Test listing OUs for root parent"""
    # Arrange
    root_id = "r-1234"
    root_ous = [
        {"Id": "ou-5678", "Name": "Department1"},
        {"Id": "ou-9012", "Name": "Department2"}
    ]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"OrganizationalUnits": root_ous}]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_organizational_units_for_parent(root_id)

    # Assert
    assert result == root_ous
    assert cache.get(f'children_{root_id}') == root_ous
    paginator_mock.paginate.assert_called_once_with(ParentId=root_id)


def test_list_organizational_units_for_parent_cache_persistence(cls, cache):
    """Test cache persistence across multiple calls"""
    # Arrange
    parent_id = "ou-1234"
    expected_ous = [{"Id": "ou-5678", "Name": "Development"}]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"OrganizationalUnits": expected_ous}]
    cls.client.get_paginator.return_value = paginator_mock

    # First call - should hit API
    result1 = cls.list_organizational_units_for_parent(parent_id)

    # Reset mock
    cls.client.get_paginator.reset_mock()

    # Second call - should use cache
    result2 = cls.list_organizational_units_for_parent(parent_id)

    # Assert
    assert result1 == result2 == expected_ous
    assert cls.client.get_paginator.call_count == 0
    assert cache.get(f'children_{parent_id}') == expected_ous


def test_list_accounts_single_page(cls, cache):
    """Test listing accounts with single page response"""
    # Arrange
    expected_accounts = [
        {"Id": "123456789012", "Name": "Development", "Email": "dev@example.com", "Status": "ACTIVE"},
        {"Id": "098765432109", "Name": "Production", "Email": "prod@example.com", "Status": "ACTIVE"}
    ]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"Accounts": expected_accounts}]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_accounts()

    # Assert
    assert result == expected_accounts
    assert cache.get('accounts') == expected_accounts
    cls.client.get_paginator.assert_called_once_with('list_accounts')
    paginator_mock.paginate.assert_called_once()


def test_list_accounts_cached(cls, cache):
    """Test listing accounts when results are in cache"""
    # Arrange
    cached_accounts = [
        {"Id": "123456789012", "Name": "Development", "Email": "dev@example.com", "Status": "ACTIVE"},
        {"Id": "098765432109", "Name": "Production", "Email": "prod@example.com", "Status": "ACTIVE"}
    ]
    cache.add('accounts', cached_accounts)

    # Act
    result = cls.list_accounts()

    # Assert
    assert result == cached_accounts
    cls.client.get_paginator.assert_not_called()


def test_list_accounts_multiple_pages(cls, cache):
    """Test listing accounts with paginated results"""
    # Arrange
    page1_accounts = [
        {"Id": "123456789012", "Name": "Development", "Email": "dev@example.com", "Status": "ACTIVE"}
    ]
    page2_accounts = [
        {"Id": "098765432109", "Name": "Production", "Email": "prod@example.com", "Status": "ACTIVE"}
    ]

    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [
        {"Accounts": page1_accounts},
        {"Accounts": page2_accounts}
    ]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_accounts()

    # Assert
    assert result == page1_accounts + page2_accounts
    assert cache.get('accounts') == page1_accounts + page2_accounts
    paginator_mock.paginate.assert_called_once()


def test_list_accounts_empty(cls, cache):
    """Test listing accounts when organization has no accounts"""
    # Arrange
    paginator_mock = Mock()
    paginator_mock.paginate.return_value = [{"Accounts": []}]
    cls.client.get_paginator.return_value = paginator_mock

    # Act
    result = cls.list_accounts()

    # Assert
    assert result == []
    assert cache.get('accounts') == []
    paginator_mock.paginate.assert_called_once()


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
            "OrganizationalUnits": [
                {"Id": "ou-080922", "Arn": "", "Name": "banking"},
            ],
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"}
            ],
        }

        list_organizational_units_for_investment_response = {
            "OrganizationalUnits": [],
        }

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
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
                {"Id": "ou-123456", "Arn": "", "Name": "production"},
            ],
        }

        list_organizational_units_for_production_response = {
            "OrganizationalUnits": [
                {"Id": "ou-080922", "Arn": "", "Name": "banking"},
            ],
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"},
            ],
        }

        list_organizational_units_for_investment_response = {
            "OrganizationalUnits": [],
        }

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
            },
            {
                "Id": "3333333333",
                "Arn": "",
                "Email": "account+3@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
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
            "OrganizationalUnits": [
                {"Id": "ou-080922", "Arn": "", "Name": "banking"},
            ],
        }

        list_organizational_units_for_banking_response = {
            "OrganizationalUnits": [
                {"Id": "ou-09092022", "Arn": "", "Name": "investment"},
                {"Id": "ou-26092022", "Arn": "", "Name": "commercial"},
            ]
        }

        list_organizational_units_for_investment_response = {
            "OrganizationalUnits": [],
        }

        list_organizational_units_for_commercial_response = {
            "OrganizationalUnits": [],
        }

        list_accounts_for_banking_response_page_0 = {
            "Accounts": [
                {
                    "Id": "11111111111",
                    "Arn": "",
                    "Email": "account+1@example.com",
                    "Status": "ACTIVE",
                    "JoinedMethod": "Invited",
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 8, 9, tzinfo=timezone.utc)
                    ),
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
                    "JoinedTimestamp": (
                        datetime(2022, 9, 26, tzinfo=timezone.utc)
                    ),
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
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
            },
            {
                "Id": "22222222222",
                "Arn": "",
                "Email": "account+2@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": (
                    datetime(2022, 8, 9, tzinfo=timezone.utc)
                ),
            },
            {
                "Id": "444444444",
                "Arn": "",
                "Email": "account+4@example.com",
                "Status": "ACTIVE",
                "JoinedMethod": "Invited",
                "JoinedTimestamp": (
                    datetime(2022, 9, 26, tzinfo=timezone.utc)
                ),
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
