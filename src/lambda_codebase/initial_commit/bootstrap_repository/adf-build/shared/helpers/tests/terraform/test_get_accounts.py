# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

import json
from mock import Mock, patch, call
import pytest
import get_accounts

# pylint: skip-file

CREDENTIALS = {
    "AccessKeyId": "access-key-id",
    "SecretAccessKey": "secret-access-key",
    "SessionToken": "session-token",
}
EXPECTED_ORG_ROLE_ARN = (
    f"arn:{get_accounts.PARTITION}:sts::"
    f"{get_accounts.MANAGEMENT_ACCOUNT_ID}:role/"
    "adf/organizations/adf-organizations-readonly"
)


# ---------------------------------------------------------------------------
# get_boto3_client
# ---------------------------------------------------------------------------
@patch("get_accounts.boto3")
@patch("get_accounts.sts")
def test_get_boto3_client_assumes_role_and_returns_client(sts_mock, boto3_mock):
    sts_mock.assume_role.return_value = {"Credentials": CREDENTIALS}
    session = Mock()
    boto3_mock.Session.return_value = session
    client = Mock()
    session.client.return_value = client

    result = get_accounts.get_boto3_client(
        "organizations",
        "arn:aws:sts::123:role/some-role",
        "session-name",
    )

    assert result is client
    sts_mock.assume_role.assert_called_once_with(
        RoleArn="arn:aws:sts::123:role/some-role",
        RoleSessionName="session-name",
        DurationSeconds=900,
    )
    boto3_mock.Session.assert_called_once_with(
        aws_access_key_id=CREDENTIALS["AccessKeyId"],
        aws_secret_access_key=CREDENTIALS["SecretAccessKey"],
        aws_session_token=CREDENTIALS["SessionToken"],
    )
    session.client.assert_called_once_with("organizations")


# ---------------------------------------------------------------------------
# get_accounts
# ---------------------------------------------------------------------------
@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_filters_active_and_maps_fields(
    get_boto3_client,
    paginator_mock,
):
    org_client = Mock()
    get_boto3_client.return_value = org_client
    paginator_mock.return_value = [
        {"Id": "111111111111", "Email": "a@example.com", "State": "ACTIVE"},
        {"Id": "222222222222", "Email": "b@example.com", "State": "SUSPENDED"},
        {"Id": "333333333333", "Email": "c@example.com", "State": "ACTIVE"},
        {"Id": "444444444444", "Email": "d@example.com", "State": "CLOSED"},
    ]

    result = get_accounts.get_accounts()

    assert result == [
        {"AccountId": "111111111111", "Email": "a@example.com"},
        {"AccountId": "333333333333", "Email": "c@example.com"},
    ]
    get_boto3_client.assert_called_once_with(
        "organizations",
        EXPECTED_ORG_ROLE_ARN,
        "getaccountIDs",
    )
    paginator_mock.assert_called_once_with(org_client.list_accounts)


@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_empty_when_no_active_accounts(
    get_boto3_client,
    paginator_mock,
):
    get_boto3_client.return_value = Mock()
    paginator_mock.return_value = [
        {"Id": "222222222222", "Email": "b@example.com", "State": "SUSPENDED"},
    ]

    assert get_accounts.get_accounts() == []


# ---------------------------------------------------------------------------
# list_organizational_units_for_parent
# ---------------------------------------------------------------------------
@patch("get_accounts.get_boto3_client")
def test_list_organizational_units_for_parent_flattens_pages(get_boto3_client):
    org_client = Mock()
    get_boto3_client.return_value = org_client
    paginator_item = Mock()
    org_client.get_paginator.return_value = paginator_item
    paginator_item.paginate.return_value = [
        {"OrganizationalUnits": [{"Id": "ou-1", "Name": "one"}]},
        {"OrganizationalUnits": [
            {"Id": "ou-2", "Name": "two"},
            {"Id": "ou-3", "Name": "three"},
        ]},
    ]

    result = get_accounts.list_organizational_units_for_parent("r-root")

    assert result == [
        {"Id": "ou-1", "Name": "one"},
        {"Id": "ou-2", "Name": "two"},
        {"Id": "ou-3", "Name": "three"},
    ]
    get_boto3_client.assert_called_once_with(
        "organizations",
        EXPECTED_ORG_ROLE_ARN,
        "getOrganizationUnits",
    )
    org_client.get_paginator.assert_called_once_with(
        "list_organizational_units_for_parent",
    )
    paginator_item.paginate.assert_called_once_with(ParentId="r-root")


# ---------------------------------------------------------------------------
# get_account_recursive
# ---------------------------------------------------------------------------
def _build_recursive_org_client(ou_children, account_children):
    """
    Build a mock organizations client whose `list_children` paginator returns
    child OUs / accounts keyed by ParentId and ChildType.
    """
    org_client = Mock()
    paginator_item = Mock()
    org_client.get_paginator.return_value = paginator_item

    def _paginate(ParentId, ChildType):
        if ChildType == "ORGANIZATIONAL_UNIT":
            children = ou_children.get(ParentId, [])
        else:
            children = account_children.get(ParentId, [])
        return [{"Children": children}]

    paginator_item.paginate.side_effect = _paginate
    return org_client, paginator_item


def test_get_account_recursive_single_level():
    org_client, paginator_item = _build_recursive_org_client(
        ou_children={"ou-parent": []},
        account_children={
            "ou-parent": [
                {"Id": "111111111111"},
                {"Id": "222222222222"},
            ],
        },
    )

    result = get_accounts.get_account_recursive(org_client, "ou-parent", "/")

    assert result == [
        {"AccountId": "111111111111"},
        {"AccountId": "222222222222"},
    ]
    org_client.get_paginator.assert_called_once_with("list_children")
    paginator_item.paginate.assert_has_calls([
        call(ParentId="ou-parent", ChildType="ORGANIZATIONAL_UNIT"),
        call(ParentId="ou-parent", ChildType="ACCOUNT"),
    ])


def test_get_account_recursive_nested_ous():
    org_client, _ = _build_recursive_org_client(
        ou_children={
            "ou-root": [{"Id": "ou-child"}],
            "ou-child": [],
        },
        account_children={
            "ou-root": [{"Id": "111111111111"}],
            "ou-child": [{"Id": "222222222222"}],
        },
    )

    result = get_accounts.get_account_recursive(org_client, "ou-root", "/")

    # Child OU accounts are collected first (depth-first), then the parent's.
    assert result == [
        {"AccountId": "222222222222"},
        {"AccountId": "111111111111"},
    ]


# ---------------------------------------------------------------------------
# get_accounts_from_ous
# ---------------------------------------------------------------------------
@patch("get_accounts.get_account_recursive")
@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_from_ous_root_path(
    get_boto3_client,
    paginator_mock,
    get_account_recursive,
):
    org_client = Mock()
    get_boto3_client.return_value = org_client
    paginator_mock.return_value = [{"Id": "r-root"}]
    get_account_recursive.return_value = [{"AccountId": "111111111111"}]

    with patch("get_accounts.TARGET_OUS", "/"):
        result = get_accounts.get_accounts_from_ous()

    assert result == [{"AccountId": "111111111111"}]
    get_boto3_client.assert_called_once_with(
        "organizations",
        EXPECTED_ORG_ROLE_ARN,
        "getRootAccountIDs",
    )
    paginator_mock.assert_called_once_with(org_client.list_roots)
    get_account_recursive.assert_called_once_with(org_client, "r-root", "/")


@patch("get_accounts.get_account_recursive")
@patch("get_accounts.list_organizational_units_for_parent")
@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_from_ous_named_path_traversal(
    get_boto3_client,
    paginator_mock,
    list_ous,
    get_account_recursive,
):
    org_client = Mock()
    get_boto3_client.return_value = org_client
    paginator_mock.return_value = [{"Id": "r-root"}]
    list_ous.side_effect = [
        [{"Id": "ou-foo", "Name": "foo"}],  # children of root
        [{"Id": "ou-bar", "Name": "bar"}],  # children of ou-foo
    ]
    get_account_recursive.return_value = [{"AccountId": "111111111111"}]

    with patch("get_accounts.TARGET_OUS", "foo/bar"):
        result = get_accounts.get_accounts_from_ous()

    assert result == [{"AccountId": "111111111111"}]
    assert list_ous.call_args_list == [call("r-root"), call("ou-foo")]
    get_account_recursive.assert_called_once_with(org_client, "ou-bar", "/")


@patch("get_accounts.get_account_recursive")
@patch("get_accounts.list_organizational_units_for_parent")
@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_from_ous_multiple_targets(
    get_boto3_client,
    paginator_mock,
    list_ous,
    get_account_recursive,
):
    org_client = Mock()
    get_boto3_client.return_value = org_client
    paginator_mock.return_value = [{"Id": "r-root"}]
    list_ous.return_value = [
        {"Id": "ou-foo", "Name": "foo"},
        {"Id": "ou-baz", "Name": "baz"},
    ]
    get_account_recursive.side_effect = [
        [{"AccountId": "111111111111"}],
        [{"AccountId": "222222222222"}],
    ]

    with patch("get_accounts.TARGET_OUS", "foo,baz"):
        result = get_accounts.get_accounts_from_ous()

    assert result == [
        {"AccountId": "111111111111"},
        {"AccountId": "222222222222"},
    ]
    get_account_recursive.assert_has_calls([
        call(org_client, "ou-foo", "/"),
        call(org_client, "ou-baz", "/"),
    ])


@patch("get_accounts.get_account_recursive")
@patch("get_accounts.list_organizational_units_for_parent")
@patch("get_accounts.paginator")
@patch("get_accounts.get_boto3_client")
def test_get_accounts_from_ous_raises_when_ou_not_found(
    get_boto3_client,
    paginator_mock,
    list_ous,
    get_account_recursive,
):
    get_boto3_client.return_value = Mock()
    paginator_mock.return_value = [{"Id": "r-root"}]
    list_ous.return_value = [{"Id": "ou-other", "Name": "other"}]

    with patch("get_accounts.TARGET_OUS", "does-not-exist"):
        with pytest.raises(ValueError):
            get_accounts.get_accounts_from_ous()

    get_account_recursive.assert_not_called()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
@patch("get_accounts.get_accounts_from_ous")
@patch("get_accounts.get_accounts")
def test_main_without_target_ous_writes_accounts_only(
    get_accounts_mock,
    get_accounts_from_ous_mock,
    tmp_path,
    monkeypatch,
):
    accounts = [{"AccountId": "111111111111", "Email": "a@example.com"}]
    get_accounts_mock.return_value = accounts
    monkeypatch.chdir(tmp_path)

    with patch("get_accounts.TARGET_OUS", None):
        get_accounts.main()

    accounts_file = tmp_path / "accounts.json"
    assert json.loads(accounts_file.read_text(encoding="utf-8")) == accounts
    assert not (tmp_path / "accounts_from_ous.json").exists()
    get_accounts_from_ous_mock.assert_not_called()


@patch("get_accounts.get_accounts_from_ous")
@patch("get_accounts.get_accounts")
def test_main_with_target_ous_writes_both_files(
    get_accounts_mock,
    get_accounts_from_ous_mock,
    tmp_path,
    monkeypatch,
):
    accounts = [{"AccountId": "111111111111", "Email": "a@example.com"}]
    accounts_from_ous = [{"AccountId": "222222222222"}]
    get_accounts_mock.return_value = accounts
    get_accounts_from_ous_mock.return_value = accounts_from_ous
    monkeypatch.chdir(tmp_path)

    with patch("get_accounts.TARGET_OUS", "/"):
        get_accounts.main()

    accounts_file = tmp_path / "accounts.json"
    ous_file = tmp_path / "accounts_from_ous.json"
    assert json.loads(accounts_file.read_text(encoding="utf-8")) == accounts
    assert (
        json.loads(ous_file.read_text(encoding="utf-8")) == accounts_from_ous
    )
    get_accounts_from_ous_mock.assert_called_once()
