# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from pytest import fixture
from ..slack import *
from .stubs.slack import stub_approval_event, stub_failed_pipeline_event, stub_bootstrap_event, stub_failed_bootstrap_event

@fixture
def stubs():
    os.environ["ADF_PIPELINE_PREFIX"] = 'adf-pipeline'

    stub_approval = stub_approval_event
    stub_failed_pipeline = stub_failed_pipeline_event
    stub_bootstrap = stub_bootstrap_event
    return stub_approval, stub_failed_pipeline, stub_bootstrap

def test_extract_message(stubs):
    message = extract_message(stub_failed_pipeline_event)
    assert message["detail-type"] == 'CodePipeline Pipeline Execution State Change'

def test_extract_pipeline(stubs):
    message = extract_message(stub_failed_pipeline_event)
    extracted_message = extract_pipeline(message)
    assert extracted_message["name"] == 'sample-vpc'
    assert extracted_message["state"] == 'FAILED'
    assert extracted_message["time"] == '3000-03-10T11:09:38Z'
    assert extracted_message["account_id"] == '2'

def test_is_approval(stubs):
    message = extract_message(stub_approval_event)
    extracted_message = is_approval(message)
    assert extracted_message['pipelineName'] == 'adf-pipeline-sample-vpc'
    assert extracted_message['stageName'] == 'approval-stage-1'

def test_is_bootstrap(stubs):
    assert is_bootstrap(stub_failed_pipeline_event) == False
    assert is_bootstrap(stub_approval_event) == False
    assert is_bootstrap(stub_bootstrap_event) == True

def test_create_approval(stubs):
    message = extract_message(stub_approval_event)
    assert bool(is_approval(message)) == True

def test_create_pipeline_message_text(stubs):
    message = extract_message(stub_failed_pipeline_event)
    extracted_message = extract_pipeline(message)
    assertion = create_pipeline_message_text('some_channel', extracted_message)
    assert assertion["channel"] == 'some_channel'
    assert assertion["text"] == ':red_circle: Pipeline sample-vpc on 2 has FAILED'

def test_create_bootstrap_message_text(stubs):
    message = extract_message(stub_bootstrap_event)
    assertion = create_bootstrap_message_text('some_channel', message)
    assert assertion["channel"] == 'some_channel'
    assert assertion["text"] == ':white_check_mark: Account 1111111 has now been bootstrapped into banking/production'

def test_create_bootstrap_message_fail_text(stubs):
    message = extract_message(stub_failed_bootstrap_event)
    assertion = create_bootstrap_message_text('some_channel', message)
    assert assertion["channel"] == 'some_channel'
    assert assertion["text"] == ':red_circle: CloudFormation Stack Failed - Account: 111 Region: eu-central-1 Status: ROLLBACK_IN_PROGRESS'