# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture
from .stubs import parameters
from mock import Mock

from parameter_store import ParameterStore


@fixture
def cls():
    cls = ParameterStore(
        'us-east-1',
        boto3
    )
    return cls


# Needs pagination and associated tests
def test_fetch_parameters_by_path(cls):
    cls.client = Mock()
    cls.client.get_parameters_by_path.return_value = parameters.stub_get_parameters_by_path
    assert cls.fetch_parameters_by_path(
        'some_path') == parameters.stub_get_parameters_by_path.get('Parameters')


def test_fetch_parameter(cls):
    cls.client = Mock()
    cls.client.get_parameter.return_value = parameters.stub_get_parameter
    assert cls.fetch_parameter('some_path') == 'some_parameter_value'
