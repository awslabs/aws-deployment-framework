# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import sys
import yaml
import boto3

from pytest import fixture
from mock import Mock
from pipeline import Pipeline


@fixture
def cls():
    return Pipeline(
        pipeline={
        "name": "pipeline",
        "params": [{"key": "value"}],
        "targets": [],
        "type": "cc-cloudformation"
        }
    )


def test_flatten_list():
    assertions = Pipeline.flatten_list([['val0', 'val1'], ['val2']])
    assert assertions == ['val0', 'val1', 'val2']


def test_generate_parameters(cls):
    parameters = cls.generate_parameters()
    assert parameters == [
        {'ParameterKey': 'ProjectName', 'ParameterValue': 'pipeline'},
        {'ParameterKey': 'key', 'ParameterValue': 'value'}
    ]
