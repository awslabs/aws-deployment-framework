# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture, raises
from stubs import stub_step_functions
from mock import Mock
from stepfunctions import StepFunctions


@fixture
def cls():
    cls = StepFunctions(
        role=boto3,
        deployment_account_id='11111111111',
        deployment_account_region='eu-central-1',
        regions=['region-1', 'region-2'],
        account_ids='99999999999',
        full_path='banking/testing',
        update_pipelines_only=0
    )

    cls.client = Mock()
    return cls


def test_statemachine_start(cls):
    cls.client.start_execution.return_value = stub_step_functions.start_execution
    cls._start_statemachine()
    assert cls.execution_arn == 'some_execution_arn'


def test_statemachine_get_status(cls):
    cls.client.describe_execution.return_value = stub_step_functions.describe_execution
    cls._start_statemachine()
    cls._fetch_statemachine_status()
    cls._execution_status == 'RUNNING'


def test_wait_failed_state_machine_execution(cls):
    stub_step_functions.describe_execution["status"] = "FAILED"
    cls.client.describe_execution.return_value = stub_step_functions.describe_execution
    cls._start_statemachine()
    cls._fetch_statemachine_status()
    assert cls._execution_status == 'FAILED'
    with raises(Exception):
        cls._wait_state_machine_execution()
