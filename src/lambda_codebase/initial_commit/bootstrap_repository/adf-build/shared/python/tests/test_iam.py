# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture
from stubs import stub_iam
from mock import Mock

from iam import IAM


@fixture
def cls():
    cls = IAM(
        boto3
    )
    cls.client = Mock()
    cls.client.get_role_policy.return_value = stub_iam.get_role_policy
    cls._fetch_policy_document('some_role_name', 'some_policy_name')
    return cls


def test_fetch_policy_document(cls):
    assert cls.role_name == 'some_role_name'
    assert cls.policy_name == 'some_policy_name'
    assert cls.policy is not None


def test_update_iam_policy_bucket(cls):
    cls._update_iam_policy_bucket('some_bucket')
    for policy in cls.policy.get('Statement'):
        if policy["Sid"] == "S3":
            assert 'arn:aws:s3:::some_bucket' in policy["Resource"]
            assert 'arn:aws:s3:::some_bucket/*' in policy["Resource"]


def test_update_iam_cfn(cls):
    cls._update_iam_cfn(
        'kms::12345678910::some_arn'
    )
    for policy in cls.policy.get('Statement'):
        if policy["Sid"] == "KMS":
            assert 'kms::12345678910::some_arn' in policy["Resource"]
