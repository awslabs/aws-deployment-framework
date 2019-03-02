# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture
from .stubs import kms
from mock import Mock

from kms import KMS


@fixture
def cls():
    cls = KMS(
        'eu-central-1',
        boto3,
        'some_kms_arn',
        '12345678910')
    cls.client = Mock()
    cls.client.get_key_policy.return_value = kms.stub_kms_get_policy
    cls._fetch_key_policy()
    return cls


def test_update_key_policy(cls):
    cls._update_key_policy()
    assert 'arn:aws:iam::12345678910:root' in cls.policy['Statement'][-1]['Principal']['AWS']
