# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture
from stubs import stub_codepipeline
from mock import Mock

from paginator import paginator
from codepipeline import CodePipeline


@fixture
def cls():
    return CodePipeline(boto3, os.environ["AWS_REGION"])


def test_get_pipeline_status(cls):
    cls.client = Mock()
    cls.client.get_pipeline_state.return_value = stub_codepipeline.get_pipeline_state
    assert cls.get_pipeline_status('my_pipeline') == 'Succeeded'
