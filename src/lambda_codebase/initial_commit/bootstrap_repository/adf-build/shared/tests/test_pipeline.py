# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import sys
import yaml
import boto3

from pytest import fixture
from ..pipeline import Pipeline


@fixture
def cls():
    return Pipeline(
        pipeline={
        "name": "pipeline",
        "params": {"key": "value"},
        "targets": [],
        "default_providers": {
            "source": {
                "name": "codecommit",
                "properties" : {
                    "account_id": 111111111111,
                }
            }
        }
    })


def test_flatten_list():
    assertions = Pipeline.flatten_list([['val0', 'val1'], ['val2']])
    assert assertions == ['val0', 'val1', 'val2']
