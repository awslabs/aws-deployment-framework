# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        "type": {
                "source": {
                    "name": "codecommit",
                    "account_id": 123456789101
                }
            }
        }
    )


def test_flatten_list():
    assertions = Pipeline.flatten_list([['val0', 'val1'], ['val2']])
    assert assertions == ['val0', 'val1', 'val2']


# def test_pipeline_init_defaults(cls):
#     assert cls.action == ''
#     assert cls.notification_endpoint is None
#     assert cls.contains_transform == ''


# def test_pipeline_replace_on_failure():
#     assertion_pipeline = Pipeline(
#         pipeline={
#             "name": "pipeline",
#             "params": {"key": "value"},
#             "targets": [],
#             "type": {
#                     "source": {
#                         "name": "codecommit",
#                         "account_id": 123456789101
#                     }
#                 }
#         }
#     )
#     assert assertion_pipeline.action == "REPLACE_ON_FAILURE"


# def test_pipeline_contains_transform():
#     assertion_pipeline = Pipeline(
#         pipeline={
#             "name": "pipeline",
#             "params": {"key": "value"},
#             "targets": [],
#             "type": {
#                     "source": {
#                         "name": "codecommit",
#                         "account_id": 123456789101
#                     }
#                 }
#         }
#     )
#     assert assertion_pipeline.contains_transform == "true"
