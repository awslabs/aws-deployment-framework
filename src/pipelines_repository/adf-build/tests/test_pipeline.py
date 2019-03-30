# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import sys
import yaml
import boto3

from pytest import fixture
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


def test_pipeline_init_defaults(cls):
    assert cls.replace_on_failure is None
    assert cls.notification_endpoint is None


def test_pipeline_replace_on_failure():
    assertion_pipeline = Pipeline(
        pipeline={
        "name": "pipeline",
        "params": [{"key": "value"}],
        "targets": [],
        "type": "cc-cloudformation",
        "replace_on_failure": True
        }
    )
    assert assertion_pipeline.replace_on_failure is True

def test_generate_parameters(cls):
    parameters = cls.generate_parameters()
    assert parameters == [
        {'ParameterKey': 'ProjectName', 'ParameterValue': 'pipeline'},
        {'ParameterKey': 'key', 'ParameterValue': 'value'}
    ]
