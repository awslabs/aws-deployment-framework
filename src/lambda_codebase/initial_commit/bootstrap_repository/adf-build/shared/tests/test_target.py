# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        step={}
    )
    return cls

def test_account_is_active():
    assert Target._account_is_active({'Status': 'ACTIVE'}) is True
    assert Target._account_is_active({'Status': 'FAKE'}) is False

def test_fetch_accounts_for_target_ou_path():
    cls = Target(
        path='/thing/path',
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=None,
        step={}
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
        step={}
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
        step={}
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
        step={}
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
        step={}
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()

def test_fetch_account_error_invalid_account_id():
    cls = Target(
        path='12345678910', #11 digits rather than 12 (invalid account id)
        regions=['region1', 'region2'],
        target_structure=MockTargetStructure(),
        organizations=Mock(),
        step={}
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()