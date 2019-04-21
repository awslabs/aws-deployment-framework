# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        '12345678910'
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
