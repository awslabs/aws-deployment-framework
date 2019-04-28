# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file


from pytest import fixture
from event import Event
from stubs import stub_event
from mock import Mock, patch, call
from sts import STS
from account_bootstrap import *


@fixture
def cls():
    parameter_store = Mock()
    organizations = Mock()

    parameter_store = Mock()
    parameter_store.fetch_parameter.return_value = str(stub_event.config)

    event = Event(
        event=stub_event.event,
        parameter_store=parameter_store,
        organizations=organizations,
        account_id=111111111111
    )
    event.deployment_account_region = os.environ["AWS_REGION"]
    event.cross_account_access_role = 'OrganizationAccountAccessRole'
    event.regions = ['eu-west-1', 'eu-central-1']  # Some example region
    event = event.create_output_object('/my_path/production')

    return event

@fixture
def cls_deployment_account():
    parameter_store = Mock()
    organizations = Mock()

    parameter_store = Mock()
    parameter_store.fetch_parameter.return_value = str(stub_event.config)

    event =  Event(
        event=stub_event.event,
        parameter_store=parameter_store,
        organizations=organizations,
        account_id=111111111111
    )
    event.deployment_account_region = os.environ["AWS_REGION"]
    event.cross_account_access_role = 'OrganizationAccountAccessRole'
    event.regions = ['eu-west-1', 'eu-central-1'] # Some example region
    event.is_deployment_account = 1
    event = event.create_output_object('/deployment')
    return event

@fixture
def sts():
    sts = Mock()
    sts.assume_cross_account_role.return_value = boto3
    return sts


@patch('account_bootstrap.configure_generic_account')
@patch('account_bootstrap.configure_master_account_parameters')
@patch('account_bootstrap.STS')
@patch('account_bootstrap.CloudFormation')
def test_lambda_handler(cloudformation_mock, sts_mock, configure_master_account_parameters_mock, configure_generic_account_mock, cls):
    sts_client_mock = Mock()
    sts_client_mock.assume_cross_account_role.return_value = {}


    cloudformation_client_mock = Mock()
    cloudformation_client_mock.create_stack.return_value = {}

    cloudformation_mock.return_value = cloudformation_mock
    sts_mock.return_value = sts_client_mock

    lambda_handler(cls, {})

    configure_master_account_parameters_mock.assert_not_called()
    sts_mock.assert_called_once()
    cloudformation_mock.assert_called()

@patch('account_bootstrap.configure_generic_account')
@patch('account_bootstrap.configure_master_account_parameters')
@patch('account_bootstrap.configure_deployment_account_parameters')
@patch('account_bootstrap.STS')
@patch('account_bootstrap.CloudFormation')
def test_lambda_handler_deployment_account(cloudformation_mock, sts_mock, configure_deployment_account_parameters_mock, configure_master_account_parameters_mock, configure_generic_account_mock, cls_deployment_account):
    sts_client_mock = Mock()
    sts_client_mock.assume_cross_account_role.return_value = {}

    cloudformation_client_mock = Mock()
    cloudformation_client_mock.create_stack.return_value = {}

    cloudformation_mock.return_value = cloudformation_client_mock
    sts_mock.return_value = sts_client_mock

    lambda_handler(cls_deployment_account, {})

    configure_deployment_account_parameters_mock.assert_called_once()
    configure_master_account_parameters_mock.assert_called_once()
    sts_mock.assert_called_once()
    cloudformation_mock.assert_called()
    assert 2 == cloudformation_mock.call_count

def test_configure_generic_account(sts, cls):
    with patch.object(ParameterStore, 'put_parameter') as put_mock:
        with patch.object(ParameterStore, 'fetch_parameter') as get_mock:
            configure_generic_account(sts, cls, os.environ["AWS_REGION"], boto3)
            calls = [        
                call('/cross_region/kms_arn/{0}'.format(os.environ["AWS_REGION"]))
            ]
            get_mock.assert_has_calls(calls, any_order=True)

            assert 2 == put_mock.call_count
            assert 1 == get_mock.call_count

        #parameter_store_mock.assert_has_calls(calls, any_order=True)

def test_configure_master_account_parameters(cls):
    with patch.object(ParameterStore, 'put_parameter') as mock:
        # The same value gets stored on the master and deployment account
        calls = [        
            call('deployment_account_id', 111111111111), 
            call('deployment_account_id', 111111111111)
        ]
        configure_master_account_parameters(cls)
        assert 2 == mock.call_count
        mock.assert_has_calls(calls, any_order=True)

def test_configure_deployment_account_parameters(cls):
    with patch.object(ParameterStore, 'put_parameter') as mock:
        configure_deployment_account_parameters(cls, boto3)
        assert 12 == mock.call_count
