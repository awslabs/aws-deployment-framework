# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture
from stubs import stub_cloudformation
from mock import Mock

from cloudformation import CloudFormation
from s3 import S3

s3 = S3('us-east-1', 'some_bucket')


@fixture
def regional_cls():
    return CloudFormation(
        region='eu-central-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name='some_stack',
        template_url='https://some/path/regional.yml',
        s3=None,
        s3_key_path=None,
        account_id=123
    )


@fixture
def global_cls():
    return CloudFormation(
        region='us-east-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='/some/location',
        account_id=123
    )


def test_regional_get_geo_prefix(regional_cls):
    assert regional_cls._get_geo_prefix() == 'regional'


def test_regional_get_stack_name(regional_cls):
    assert regional_cls.stack_name == 'some_stack'


def test_global_get_geo_prefix(global_cls):
    assert global_cls._get_geo_prefix() == 'global'


def test_global_get_stack_name(global_cls):
    assert global_cls.stack_name == 'adf-global-base-location'


def test_get_stack_regional_outputs(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls.get_stack_regional_outputs() == {
        'kms_arn': 'some_key_arn', 's3_regional_bucket': 'some_bucket_name'}


def test_get_stack_status(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls.get_stack_status() == 'CREATE_IN_PROGRESS'


def test_get_change_set_type_update(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls._get_change_set_type() == 'UPDATE'


def test_get_change_set_type_create(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {'Stacks': []}
    assert global_cls._get_change_set_type() == 'CREATE'


def test_get_waiter_type_update_complete(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls._get_waiter_type() == 'stack_update_complete'


def test_get_waiter_type_create_complete(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {'Stacks': []}
    assert global_cls._get_waiter_type() == 'stack_create_complete'
