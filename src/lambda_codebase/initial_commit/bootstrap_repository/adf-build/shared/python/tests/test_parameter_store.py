# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture, mark
from stubs import stub_parameter_store
from mock import Mock

from parameter_store import ParameterStore


@fixture
def cls():
    cls = ParameterStore(
        'us-east-1',
        boto3
    )
    return cls


@mark.parametrize(
    "input_name, output_path",
    [
        ('/adf/test', '/adf/test'),
        ('adf/test', '/adf/test'),
        ('/test', '/test'),
        ('test', '/test'),
        ('/other/test', '/other/test'),
        ('other/test', '/other/test'),
    ],
)
def test_build_param_name_not_adf_only(input_name, output_path):
    assert ParameterStore._build_param_name(
        input_name,
        adf_only=False,
    ) == output_path


@mark.parametrize(
    "input_name, output_path",
    [
        ('/adf/test', '/adf/test'),
        ('adf/test', '/adf/test'),
        ('/test', '/adf/test'),
        ('test', '/adf/test'),
        ('/other/test', '/adf/other/test'),
        ('other/test', '/adf/other/test'),
    ],
)
def test_build_param_name_adf_only(input_name, output_path):
    assert ParameterStore._build_param_name(input_name) == output_path


def test_fetch_parameter(cls):
    cls.client = Mock()
    cls.client.get_parameter.return_value = stub_parameter_store.get_parameter
    assert cls.fetch_parameter('some_path') == 'some_parameter_value'
