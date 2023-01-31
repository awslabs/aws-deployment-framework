# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3

from pytest import fixture
from stubs import stub_organizations
from mock import Mock, patch
from cache import Cache
from organizations import Organizations


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
    cls.client.list_parents.assert_called_once_with(
        ChildId=cls.account_id,
    )


def test_get_parent_info_specific_account(cls):
    specific_account_id = '111111111111'
    cls.client = Mock()
    cls.client.list_parents.return_value = stub_organizations.list_parents
    assert cls.get_parent_info(specific_account_id) == {
        "ou_parent_id": 'some_id',
        "ou_parent_type": 'ORGANIZATIONAL_UNIT'
    }
    cls.client.list_parents.assert_called_once_with(
        ChildId=specific_account_id,
    )


@patch('organizations.paginator')
def test_get_accounts(paginator_mock, cls):
    all_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
        '444444444444',
    ]
    root_account_ids = [
        '333333333333',
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda account_id: (
        {
            "Id": (
                f"r-{account_id}" if account_id in root_account_ids
                else f"ou-{account_id}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }
    )
    paginator_mock.return_value = list(map(
        lambda account_id: ({
            "Id": account_id,
            "Status": "ACTIVE",
        }),
        all_account_ids,
    ))
    assert set(map(
        lambda account: account['Id'],
        cls.get_accounts(),
    )) == set(all_account_ids)


@patch('organizations.paginator')
def test_get_accounts_with_suspended(paginator_mock, cls):
    all_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
        '444444444444',
    ]
    root_account_ids = [
        '333333333333',
    ]
    suspended_account_ids = [
        '444444444444',
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda account_id: (
        {
            "Id": (
                f"r-{account_id}" if account_id in root_account_ids
                else f"ou-{account_id}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }
    )
    paginator_mock.return_value = list(map(
        lambda account_id: ({
            "Id": account_id,
            "Status": (
                "SUSPENDED" if account_id in suspended_account_ids
                else "ACTIVE"
            ),
        }),
        all_account_ids,
    ))
    assert set(map(
        lambda account: account['Id'],
        cls.get_accounts(),
    )) == (set(all_account_ids) - set(suspended_account_ids))


@patch('organizations.paginator')
def test_get_accounts_ignore_root(paginator_mock, cls):
    all_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
        '444444444444',
    ]
    root_account_ids = [
        '444444444444',
    ]
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: ({
        "Parents": [{
            "Id": (
                f"r-{ChildId}" if ChildId in root_account_ids
                else f"ou-{ChildId}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }],
    })
    paginator_mock.return_value = list(map(
        lambda account_id: ({
            "Id": account_id,
            "Status": "ACTIVE",
        }),
        all_account_ids,
    ))
    assert set(map(
        lambda account: account['Id'],
        cls.get_accounts(
            include_root=False,
        ),
    )) == (set(all_account_ids) - set(root_account_ids))


@patch('organizations.paginator')
def test_get_accounts_ignore_protected(paginator_mock, cls):
    all_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
        '444444444444',
    ]
    root_account_ids = [
        '444444444444',
    ]
    protected_account_ids = [
        '222222222222',
    ]
    protected_ou_ids = list(map(
        lambda account_id: f"ou-{account_id}",
        protected_account_ids,
    ))
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: ({
        "Parents": [{
            "Id": (
                f"r-{ChildId}" if ChildId in root_account_ids
                else f"ou-{ChildId}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }],
    })
    paginator_mock.return_value = list(map(
        lambda account_id: ({
            "Id": account_id,
            "Status": "ACTIVE",
        }),
        all_account_ids,
    ))
    assert set(map(
        lambda account: account['Id'],
        cls.get_accounts(
            protected_ou_ids=protected_ou_ids,
        ),
    )) == (set(all_account_ids) - set(protected_account_ids))


@patch('organizations.paginator')
def test_get_accounts_ignore_root_protected_and_inactive(paginator_mock, cls):
    all_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
        '444444444444',
        '555555555555',
        '666666666666',
        '777777777777',
        '888888888888',
    ]
    protected_account_ids = [
        '222222222222',
        '777777777777',
    ]
    root_account_ids = [
        '333333333333',
        '888888888888',
    ]
    suspended_account_ids = [
        '444444444444',
    ]
    pending_closure_account_ids = [
        '555555555555',
    ]
    protected_ou_ids = list(map(
        lambda account_id: f"ou-{account_id}",
        protected_account_ids,
    ))
    cls.client = Mock()
    cls.client.list_parents.side_effect = lambda ChildId: ({
        "Parents": [{
            "Id": (
                f"r-{ChildId}" if ChildId in root_account_ids
                else f"ou-{ChildId}"
            ),
            "Type": "ORGANIZATIONAL_UNIT",
        }],
    })
    paginator_mock.return_value = list(map(
        lambda account_id: ({
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
        }),
        all_account_ids,
    ))
    assert set(map(
        lambda account: account['Id'],
        cls.get_accounts(
            protected_ou_ids=protected_ou_ids,
            include_root=False,
        ),
    )) == (
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
        'organization_id': 'some_org_id',
        'organization_master_account_id': 'some_master_account_id',
        'feature_set': 'ALL'
    }


def test_describe_ou_name(cls):
    cls.client = Mock()
    cls.client.describe_organizational_unit.return_value = (
        stub_organizations.describe_organizational_unit
    )
    assert cls.describe_ou_name('some_ou_id') == 'some_ou_name'


def test_describe_account_name(cls):
    cls.client = Mock()
    cls.client.describe_account.return_value = (
        stub_organizations.describe_account
    )
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
    cls.client.describe_organizational_unit.return_value = (
        stub_organizations.describe_organizational_unit
    )

    assert cls.build_account_path('some_ou_id', [], cache) == 'some_ou_name'
