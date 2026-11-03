# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

import json
import tempfile
from mock import Mock, patch, call
import pytest
from botocore.exceptions import ClientError
import retrieve_organization_accounts as roa

# pylint: skip-file

DEFAULT_FIELDS = ["Id", "Email", "Name"]
CREDENTIALS = {
    "AccessKeyId": "access-key-id",
    "SecretAccessKey": "secret-access-key",
    "SessionToken": "session-token",
}


def _account(account_id, state, **extra):
    """Build a ListAccounts style account dict for the given state."""
    account = {
        "Id": account_id,
        "Arn": f"arn:aws:organizations::123456789012:account/o-abc/{account_id}",
        "Email": f"{account_id}@example.com",
        "Name": f"account-{account_id}",
        "State": state,
        "JoinedMethod": "CREATED",
    }
    account.update(extra)
    return account


# ---------------------------------------------------------------------------
# _get_partition
# ---------------------------------------------------------------------------
def test_get_partition_commercial():
    assert roa._get_partition("us-east-1") == "aws"
    assert roa._get_partition("eu-central-1") == "aws"


def test_get_partition_gov_cloud():
    assert roa._get_partition("us-gov-west-1") == "aws-us-gov"
    assert roa._get_partition("us-gov-east-1") == "aws-us-gov"


# ---------------------------------------------------------------------------
# _get_billing_account_id
# ---------------------------------------------------------------------------
@patch("retrieve_organization_accounts.boto3")
def test_get_billing_account_id(boto3_mock):
    org_client = Mock()
    boto3_mock.client.return_value = org_client
    org_client.describe_organization.return_value = {
        "Organization": {
            "MasterAccountId": "111111111111",
        },
    }

    assert roa._get_billing_account_id() == "111111111111"
    boto3_mock.client.assert_called_once_with("organizations")


# ---------------------------------------------------------------------------
# _get_member_accounts
# ---------------------------------------------------------------------------
def _setup_member_accounts_mocks(boto3_mock, pages):
    """Wire up the boto3 Session -> org client -> paginator mock chain."""
    session = Mock()
    boto3_mock.Session.return_value = session
    org_client = Mock()
    session.client.return_value = org_client
    paginator = Mock()
    org_client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages
    return session, org_client, paginator


@patch("retrieve_organization_accounts._request_sts_credentials")
@patch("retrieve_organization_accounts.boto3")
def test_get_member_accounts_derives_status_from_state(
    boto3_mock,
    request_sts_credentials,
):
    request_sts_credentials.return_value = CREDENTIALS
    _setup_member_accounts_mocks(
        boto3_mock,
        pages=[
            {
                "Accounts": [
                    _account("111111111111", "ACTIVE"),
                ],
            },
        ],
    )
    options = {"--field": ["Id", "State", "Status"]}

    result = roa._get_member_accounts(
        billing_account_id="999999999999",
        options=options,
    )

    assert result == [
        {
            "Id": "111111111111",
            "State": "ACTIVE",
            "Status": "ACTIVE",
        },
    ]


@patch("retrieve_organization_accounts._request_sts_credentials")
@patch("retrieve_organization_accounts.boto3")
def test_get_member_accounts_only_returns_active_accounts(
    boto3_mock,
    request_sts_credentials,
):
    request_sts_credentials.return_value = CREDENTIALS
    _setup_member_accounts_mocks(
        boto3_mock,
        pages=[
            {
                "Accounts": [
                    _account("111111111111", "ACTIVE"),
                    _account("222222222222", "SUSPENDED"),
                    _account("333333333333", "PENDING_CLOSURE"),
                    _account("444444444444", "CLOSED"),
                    _account("555555555555", "PENDING_ACTIVATION"),
                ],
            },
        ],
    )
    options = {"--field": ["Id"]}

    result = roa._get_member_accounts(
        billing_account_id="999999999999",
        options=options,
    )

    # Only the ACTIVE state account should be returned.
    assert result == [{"Id": "111111111111"}]


@patch("retrieve_organization_accounts._request_sts_credentials")
@patch("retrieve_organization_accounts.boto3")
def test_get_member_accounts_filters_to_requested_fields(
    boto3_mock,
    request_sts_credentials,
):
    request_sts_credentials.return_value = CREDENTIALS
    _setup_member_accounts_mocks(
        boto3_mock,
        pages=[
            {
                "Accounts": [
                    _account("111111111111", "ACTIVE"),
                ],
            },
        ],
    )
    options = {"--field": DEFAULT_FIELDS}

    result = roa._get_member_accounts(
        billing_account_id="999999999999",
        options=options,
    )

    assert result == [
        {
            "Id": "111111111111",
            "Email": "111111111111@example.com",
            "Name": "account-111111111111",
        },
    ]
    # Fields not requested must not leak through.
    assert "State" not in result[0]
    assert "Status" not in result[0]
    assert "Arn" not in result[0]


@patch("retrieve_organization_accounts._request_sts_credentials")
@patch("retrieve_organization_accounts.boto3")
def test_get_member_accounts_paginates_over_all_pages(
    boto3_mock,
    request_sts_credentials,
):
    request_sts_credentials.return_value = CREDENTIALS
    _setup_member_accounts_mocks(
        boto3_mock,
        pages=[
            {"Accounts": [_account("111111111111", "ACTIVE")]},
            {"Accounts": [_account("222222222222", "ACTIVE")]},
        ],
    )
    options = {"--field": ["Id"]}

    result = roa._get_member_accounts(
        billing_account_id="999999999999",
        options=options,
    )

    assert result == [
        {"Id": "111111111111"},
        {"Id": "222222222222"},
    ]


@patch("retrieve_organization_accounts._request_sts_credentials")
@patch("retrieve_organization_accounts.boto3")
def test_get_member_accounts_uses_assumed_credentials(
    boto3_mock,
    request_sts_credentials,
):
    request_sts_credentials.return_value = CREDENTIALS
    _setup_member_accounts_mocks(
        boto3_mock,
        pages=[{"Accounts": []}],
    )
    options = {"--field": ["Id"]}

    roa._get_member_accounts(
        billing_account_id="999999999999",
        options=options,
    )

    boto3_mock.Session.assert_called_once_with(
        aws_access_key_id=CREDENTIALS["AccessKeyId"],
        aws_secret_access_key=CREDENTIALS["SecretAccessKey"],
        aws_session_token=CREDENTIALS["SessionToken"],
    )
    boto3_mock.Session.return_value.client.assert_called_once_with(
        "organizations",
    )


# ---------------------------------------------------------------------------
# _request_sts_credentials
# ---------------------------------------------------------------------------
@patch("retrieve_organization_accounts.boto3")
def test_request_sts_credentials_success(boto3_mock):
    session = Mock()
    boto3_mock.session.Session.return_value = session
    session.region_name = "eu-central-1"
    sts_client = Mock()
    session.client.return_value = sts_client
    sts_client.assume_role.return_value = {
        "Credentials": CREDENTIALS,
    }
    options = {
        "--role-name": "adf/organizations/adf-organizations-readonly",
        "--session-name": "retrieve_organization_accounts",
        "--session-ttl": "900",
    }

    result = roa._request_sts_credentials(
        billing_account_id="111111111111",
        options=options,
    )

    assert result == CREDENTIALS
    sts_client.assume_role.assert_called_once_with(
        RoleArn=(
            "arn:aws:iam::111111111111:role/"
            "adf/organizations/adf-organizations-readonly"
        ),
        RoleSessionName="retrieve_organization_accounts",
        DurationSeconds=900,
    )


@patch("retrieve_organization_accounts.boto3")
def test_request_sts_credentials_gov_partition(boto3_mock):
    session = Mock()
    boto3_mock.session.Session.return_value = session
    session.region_name = "us-gov-west-1"
    sts_client = Mock()
    session.client.return_value = sts_client
    sts_client.assume_role.return_value = {"Credentials": CREDENTIALS}
    options = {
        "--role-name": "some-role",
        "--session-name": "session",
        "--session-ttl": "900",
    }

    roa._request_sts_credentials(
        billing_account_id="111111111111",
        options=options,
    )

    _, kwargs = sts_client.assume_role.call_args
    assert kwargs["RoleArn"] == (
        "arn:aws-us-gov:iam::111111111111:role/some-role"
    )


@patch("retrieve_organization_accounts.boto3")
def test_request_sts_credentials_raises_on_client_error(boto3_mock):
    session = Mock()
    boto3_mock.session.Session.return_value = session
    session.region_name = "eu-central-1"
    sts_client = Mock()
    session.client.return_value = sts_client
    sts_client.assume_role.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}},
        "AssumeRole",
    )
    options = {
        "--role-name": "some-role",
        "--session-name": "session",
        "--session-ttl": "900",
    }

    with pytest.raises(ClientError):
        roa._request_sts_credentials(
            billing_account_id="111111111111",
            options=options,
        )


# ---------------------------------------------------------------------------
# _flush_out
# ---------------------------------------------------------------------------
@patch("retrieve_organization_accounts.LOGGER")
def test_flush_out_to_stdout_logs_accounts(logger_mock):
    accounts = [{"Id": "111111111111"}]
    options = {"--output-file": "-"}

    roa._flush_out(accounts=accounts, options=options)

    logger_mock.info.assert_called_once_with(
        "Accounts JSON: %s",
        json.dumps(accounts, indent=2, default=str),
    )


def test_flush_out_to_file_writes_json():
    accounts = [
        {"Id": "111111111111", "State": "ACTIVE", "Status": "ACTIVE"},
        {"Id": "222222222222", "State": "ACTIVE", "Status": "ACTIVE"},
    ]
    with tempfile.NamedTemporaryFile(mode="r", suffix=".json") as output_file:
        options = {"--output-file": output_file.name}

        roa._flush_out(accounts=accounts, options=options)

        output_file.seek(0)
        assert json.load(output_file) == accounts
