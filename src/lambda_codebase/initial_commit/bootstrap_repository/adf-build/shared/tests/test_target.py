# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from errors import InvalidDeploymentMapError
from pytest import fixture, raises
from mock import Mock, patch
from .stubs import stub_target
from ..target import Target


class MockTargetStructure:
    def __init__(self):
        self.account_list = []


@fixture
def cls():
    cls = Target(
        path='/thing/path',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step_name=None,
        params={}
    )
    return cls


def test_target_is_approval(cls):
    cls.target_structure.account_list.append(
        cls._create_target_info(
            'approval',
            'approval'
        )
    )
    assert stub_target.target_is_approval in cls.target_structure.account_list


def test_account_is_active():
    assert Target._account_is_active({'Status': 'ACTIVE'}) is True
    assert Target._account_is_active({'Status': 'FAKE'}) is False


def test_create_target_info_default(cls):
    assertion = cls._create_target_info('account_name', 12345678910)
    assert assertion == stub_target.create_target_info_default


def test_create_target_info_regex(cls):
    """
    Testing account name Regex with symbol such as + or space
    """
    assertion_plus = cls._create_target_info('account+name', 12345678910)
    assertion_space = cls._create_target_info('account name', 12345678910)
    assert assertion_plus and assertion_space == stub_target.create_target_info_regex_applied


def test_target_is_account_id(cls):
    cls.organizations = Mock()
    cls.organizations.client.describe_account.return_value = stub_target.organizations_describe_account
    cls._target_is_account_id()

    assert len(cls.target_structure.account_list) is 1
    assert stub_target.target_output in cls.target_structure.account_list


def test_target_is_ou_id(cls):
    cls.organizations = Mock()
    cls.organizations.get_accounts_for_parent.return_value = stub_target.organizations_list_accounts_for_parent()
    cls._target_is_ou_id()

    assert len(cls.target_structure.account_list) is 1
    assert stub_target.target_output in cls.target_structure.account_list


def test_target_is_ou_path(cls):
    cls.organizations = Mock()
    cls.organizations.dir_to_ou.return_value = stub_target.organizations_dir_to_ou()
    cls._target_is_ou_path()

    assert stub_target.target_output in cls.target_structure.account_list
    assert len(cls.target_structure.account_list) is 1


def test_fetch_accounts_for_target_ou_path():
    cls = Target(
        path='/thing/path',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step_name=None,
        params={}
    )

    with patch.object(cls, '_target_is_ou_path') as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_target_account_id():
    cls = Target(
        path='123456789102',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step_name=None,
        params={}
    )
    with patch.object(cls, '_target_is_account_id') as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_target_ou_id():
    cls = Target(
        path='ou-123fake',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step_name=None,
        params={}
    )
    with patch.object(cls, '_target_is_ou_id') as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_approval():
    cls = Target(
        path='approval',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step_name=None,
        params={}
    )
    with patch.object(cls, '_target_is_approval') as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()

def test_fetch_account_error():
    cls = Target(
        path='some_string',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=Mock(),
        step_name=None,
        params={}
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()

def test_fetch_account_error_invalid_account_id():
    cls = Target(
        path='12345678910', #11 digits rather than 12 (invalid account id)
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=Mock(),
        step_name=None,
        params={}
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()