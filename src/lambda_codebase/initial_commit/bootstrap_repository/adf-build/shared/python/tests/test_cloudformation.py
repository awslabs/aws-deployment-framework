# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from botocore.stub import Stubber
from pytest import fixture, raises
from stubs import stub_cloudformation
from mock import Mock, call, patch

from cloudformation import CloudFormation, StackProperties
from s3 import S3

s3 = S3('us-east-1', 'some_bucket')


@fixture
def regional_cls():
    return CloudFormation(
        region='eu-central-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name='some_stack',
        template_url='https://some/path/regional.yml',
        s3=None,
        s3_key_path=None,
        account_id=123
    )


@fixture
def global_cls():
    return CloudFormation(
        region='us-east-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-bootstrap/some-ou',
        account_id=123
    )


def test_regional_get_geo_prefix(regional_cls):
    assert regional_cls._get_geo_prefix() == 'regional'


def test_regional_get_stack_name(regional_cls):
    assert regional_cls.stack_name == 'some_stack'


def test_global_get_geo_prefix(global_cls):
    assert global_cls._get_geo_prefix() == 'global'


def test_global_get_stack_name(global_cls):
    assert global_cls.stack_name == 'adf-global-base-bootstrap'


def test_global_build_get_stack_name():
    cfn = CloudFormation(
        region='us-east-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-build',
        account_id=123
    )
    assert cfn.stack_name == 'adf-global-base-adf-build'


def test_global_deployment_get_stack_name():
    cfn = CloudFormation(
        region='us-east-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-bootstrap/deployment',
        account_id=123
    )
    assert cfn.stack_name == 'adf-global-base-deployment'


def test_regional_deployment_get_stack_name():
    cfn = CloudFormation(
        region='eu-west-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-bootstrap/deployment',
        account_id=123
    )
    assert cfn.stack_name == 'adf-regional-base-deployment'


def test_regional_target_get_stack_name():
    cfn = CloudFormation(
        region='eu-west-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-bootstrap/some/ou/path',
        account_id=123
    )
    assert cfn.stack_name == 'adf-regional-base-bootstrap'


def test_get_stack_regional_outputs(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls.get_stack_regional_outputs() == {
        'kms_arn': 'some_key_arn',
        's3_regional_bucket': 'some_bucket_name',
    }


def test_get_stack_status(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls.get_stack_status() == 'CREATE_IN_PROGRESS'


def test_get_change_set_type_update(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls._get_change_set_type() == 'UPDATE'


def test_get_change_set_type_create(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {'Stacks': []}
    assert global_cls._get_change_set_type() == 'CREATE'


def test_get_waiter_type_update_complete(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = stub_cloudformation.describe_stack
    assert global_cls._get_waiter_type() == 'stack_update_complete'


def test_get_waiter_type_create_complete(global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {'Stacks': []}
    assert global_cls._get_waiter_type() == 'stack_create_complete'


def test_get_stack_name_remove_unaccepted_chars():
    for unaccepted_char in [' ', '%', '$', '*']:
        props = StackProperties(
            region='eu-central-1',
            deployment_account_region='eu-west-1',
            stack_name=None,
            s3=None,
            s3_key_path='/some/weird{}location'.format(unaccepted_char),
        )
        assert props._get_stack_name() == 'adf-regional-base-bootstrap'


@patch('cloudformation.LOGGER')
def test_describe_stack_status_success(logger, global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    response = global_cls._get_stack_status('adf-global-base-iam')
    assert response == 'CREATE_COMPLETE'
    global_cls.client.describe_stacks.assert_has_calls([
        call(StackName='adf-global-base-iam'),
    ])
    assert global_cls.client.describe_stacks.call_count == 1
    logger.error.assert_not_called()


@patch('cloudformation.LOGGER')
def test_describe_stack_status_empty_stack_list(logger, global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = {
        "Stacks": []
    }
    response = global_cls._get_stack_status('adf-global-base-iam')
    assert response is None
    global_cls.client.describe_stacks.assert_has_calls([
        call(StackName='adf-global-base-iam'),
    ])
    assert global_cls.client.describe_stacks.call_count == 1
    logger.error.assert_not_called()


@patch('cloudformation.LOGGER')
def test_describe_stack_status_empty_response(logger, global_cls):
    global_cls.client = Mock()
    global_cls.client.describe_stacks.return_value = None
    response = global_cls._get_stack_status('adf-global-base-iam')
    assert response is None
    global_cls.client.describe_stacks.assert_has_calls([
        call(StackName='adf-global-base-iam'),
    ])
    assert global_cls.client.describe_stacks.call_count == 1
    logger.error.assert_not_called()


@patch('cloudformation.LOGGER')
def test_describe_stack_status_raises_validation_error(logger, global_cls):
    client = boto3.client('cloudformation')
    stubber = Stubber(client)
    stubber.add_client_error('describe_stacks', service_error_code='ValidationError')
    stubber.activate()
    global_cls.client = client
    response = global_cls._get_stack_status('adf-global-base-iam')
    assert response is None
    logger.error.assert_not_called()


@patch('cloudformation.LOGGER')
def test_describe_stack_status_raises_other_error(logger, global_cls):
    client = boto3.client('cloudformation')
    stubber = Stubber(client)
    stubber.add_client_error('describe_stacks', service_error_code='ClientError')
    stubber.activate()
    global_cls.client = client
    with raises(Exception):
        global_cls._get_stack_status('adf-global-base-iam')
    logger.error.assert_has_calls([
        call(
            "%s in %s - Retrieve stack status of: %s failed (%s): %s",
            global_cls.account_id,
            global_cls.region,
            'adf-global-base-iam',
            'ClientError',
            '',
        )
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_all_base_stacks(paginator_mock, logger, global_cls):
    global_cls.client = Mock()
    paginator_mock.return_value = stub_cloudformation.list_stacks.get('StackSummaries')
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    global_cls.delete_all_base_stacks()
    global_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-global-base-iam'),
        call(StackName='adf-global-base-bootstrap'),
        call(StackName='adf-regional-base-bootstrap'),
        call(StackName='adf-global-base-deployment'),
        call(StackName='adf-global-base-deployment-SomeOtherStack'),
        call(StackName='adf-global-base-adf-build'),
        call(StackName='adf-global-base-dev'),
        call(StackName='adf-global-base-test'),
        call(StackName='adf-global-base-acceptance'),
        call(StackName='adf-global-base-prod'),
    ])
    assert global_cls.client.delete_stack.call_count == 10
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-global-base-iam'),
        # ^ We are deploying in a global region, not regional
        call('Removing stack: %s', 'adf-global-base-bootstrap'),
        call('Removing stack: %s', 'adf-regional-base-bootstrap'),
        call('Removing stack: %s', 'adf-global-base-deployment'),
        call('Removing stack: %s', 'adf-global-base-deployment-SomeOtherStack'),
        call('Removing stack: %s', 'adf-global-base-adf-build'),
        call('Removing stack: %s', 'adf-global-base-dev'),
        call('Removing stack: %s', 'adf-global-base-test'),
        call('Removing stack: %s', 'adf-global-base-acceptance'),
        call('Removing stack: %s', 'adf-global-base-prod'),
        call(
            'Please remove stack %s manually, state %s implies that it '
            'cannot be deleted automatically',
            'adf-global-base-some-ou',
            'CREATE_IN_PROGRESS',
        ),
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_some_deletions(paginator_mock, logger, global_cls):
    global_cls.client = Mock()
    paginator_mock.return_value = stub_cloudformation.list_stacks.get('StackSummaries')
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    global_cls.delete_deprecated_base_stacks()
    global_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-global-base-iam'),
        call(StackName='adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call(StackName='adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call(StackName='adf-global-base-deployment-SomeOtherStack'),
        call(StackName='adf-global-base-dev'),
        call(StackName='adf-global-base-test'),
        call(StackName='adf-global-base-acceptance'),
        call(StackName='adf-global-base-prod'),
    ])
    assert global_cls.client.delete_stack.call_count == 8
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-global-base-iam'),
        # ^ As we delete a bootstrap stack we need to recreate the IAM stack,
        # hence deleting it.
        call('Removing stack: %s', 'adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call('Removing stack: %s', 'adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call('Removing stack: %s', 'adf-global-base-deployment-SomeOtherStack'),
        call('Removing stack: %s', 'adf-global-base-dev'),
        call('Removing stack: %s', 'adf-global-base-test'),
        call('Removing stack: %s', 'adf-global-base-acceptance'),
        call('Removing stack: %s', 'adf-global-base-prod'),
        call(
            'Please remove stack %s manually, state %s implies that it '
            'cannot be deleted automatically',
            'adf-global-base-some-ou',
            'CREATE_IN_PROGRESS',
        ),
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_management_account_adf_build(paginator_mock, logger):
    global_cls = CloudFormation(
        region='us-east-1',
        deployment_account_region='us-east-1',
        role=boto3,
        wait=False,
        stack_name=None,
        template_url='https://some/path/global.yml',
        s3=None,
        s3_key_path='adf-build',
        account_id=123
    )
    global_cls.client = Mock()
    paginator_mock.return_value = stub_cloudformation.list_stacks.get('StackSummaries')
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    global_cls.delete_deprecated_base_stacks()
    global_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-global-base-iam'),
        call(StackName='adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call(StackName='adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call(StackName='adf-global-base-deployment-SomeOtherStack'),
        call(StackName='adf-global-base-dev'),
        call(StackName='adf-global-base-test'),
        call(StackName='adf-global-base-acceptance'),
        call(StackName='adf-global-base-prod'),
    ])
    assert global_cls.client.delete_stack.call_count == 8
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-global-base-iam'),
        # ^ As we delete a bootstrap stack we need to recreate the IAM stack,
        # hence deleting it.
        call('Removing stack: %s', 'adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call('Removing stack: %s', 'adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call('Removing stack: %s', 'adf-global-base-deployment-SomeOtherStack'),
        call('Removing stack: %s', 'adf-global-base-dev'),
        call('Removing stack: %s', 'adf-global-base-test'),
        call('Removing stack: %s', 'adf-global-base-acceptance'),
        call('Removing stack: %s', 'adf-global-base-prod'),
        call(
            'Please remove stack %s manually, state %s implies that it '
            'cannot be deleted automatically',
            'adf-global-base-some-ou',
            'CREATE_IN_PROGRESS',
        ),
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_no_iam(paginator_mock, logger, global_cls):
    global_cls.client = Mock()
    paginator_mock.return_value = list(filter(
        lambda stack: stack.get('StackName') != 'adf-global-base-iam',
        stub_cloudformation.list_stacks.get('StackSummaries'),
    ))
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [],
    }
    global_cls.delete_deprecated_base_stacks()
    global_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call(StackName='adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call(StackName='adf-global-base-deployment-SomeOtherStack'),
        call(StackName='adf-global-base-dev'),
        call(StackName='adf-global-base-test'),
        call(StackName='adf-global-base-acceptance'),
        call(StackName='adf-global-base-prod'),
    ])
    assert global_cls.client.delete_stack.call_count == 7
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-regional-base-bootstrap'),
        # ^ We are deploying in a global region, not regional
        call('Removing stack: %s', 'adf-global-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call('Removing stack: %s', 'adf-global-base-deployment-SomeOtherStack'),
        call('Removing stack: %s', 'adf-global-base-dev'),
        call('Removing stack: %s', 'adf-global-base-test'),
        call('Removing stack: %s', 'adf-global-base-acceptance'),
        call('Removing stack: %s', 'adf-global-base-prod'),
        call(
            'Please remove stack %s manually, state %s implies that it '
            'cannot be deleted automatically',
            'adf-global-base-some-ou',
            'CREATE_IN_PROGRESS',
        ),
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_all_valid(paginator_mock, logger, global_cls):
    global_cls.client = Mock()
    paginator_mock.return_value = list(filter(
        lambda stack: stack.get('StackName') in [
            'adf-global-base-bootstrap',
            'adf-global-base-iam',
        ],
        stub_cloudformation.list_stacks.get('StackSummaries'),
    ))
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    global_cls.delete_deprecated_base_stacks()
    global_cls.client.delete_stack.assert_not_called()
    logger.warning.assert_not_called()


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_only_iam(paginator_mock, logger, global_cls):
    global_cls.client = Mock()
    paginator_mock.return_value = list(filter(
        lambda stack: stack.get('StackName') in [
            'adf-global-base-iam',
        ],
        stub_cloudformation.list_stacks.get('StackSummaries'),
    ))
    global_cls.client.describe_stacks.return_value = {
        "Stacks": [
            {
                'StackName': 'adf-global-base-iam',
                'StackStatus': 'CREATE_COMPLETE',
            },
        ],
    }
    global_cls.delete_deprecated_base_stacks()
    global_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-global-base-iam'),
    ])
    assert global_cls.client.delete_stack.call_count == 1
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-global-base-iam'),
        # ^ As the IAM stack cannot live on its own, it should be deleted
    ])


@patch('cloudformation.LOGGER')
@patch("cloudformation.paginator")
def test_delete_deprecated_base_stacks_regional(paginator_mock, logger, regional_cls):
    regional_cls.client = Mock()
    regional_list_stacks = list(map(
        lambda stack: {
            **stack,
            "StackName": (
                stack.get("StackName")
                .replace("regional", "tmp")
                .replace("global", "regional")
                .replace("tmp", "global")
            ),
        },
        stub_cloudformation.list_stacks.get('StackSummaries'),
    ))
    regional_list_stacks.append({
        'StackName': 'adf-global-base-iam',
        'StackStatus': 'CREATE_COMPLETE',
    })
    paginator_mock.return_value = regional_list_stacks
    regional_cls.client.describe_stacks.return_value = {
        "Stacks": [],
    }
    regional_cls.delete_deprecated_base_stacks()
    regional_cls.client.delete_stack.assert_has_calls([
        call(StackName='adf-global-base-bootstrap'),
        # ^ We are deploying in a non-global
        call(StackName='adf-regional-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call(StackName='adf-regional-base-deployment-SomeOtherStack'),
        call(StackName='adf-regional-base-adf-build'),
        call(StackName='adf-regional-base-iam'),
        call(StackName='adf-regional-base-dev'),
        call(StackName='adf-regional-base-test'),
        call(StackName='adf-regional-base-acceptance'),
        call(StackName='adf-regional-base-prod'),
    ])
    assert regional_cls.client.delete_stack.call_count == 9
    logger.warning.assert_has_calls([
        call('Removing stack: %s', 'adf-global-base-bootstrap'),
        # ^ We are deploying in a non-global
        call('Removing stack: %s', 'adf-regional-base-deployment'),
        # ^ We are not in the deployment OU with this CloudFormation instance
        call('Removing stack: %s', 'adf-regional-base-deployment-SomeOtherStack'),
        call('Removing stack: %s', 'adf-regional-base-adf-build'),
        call('Removing stack: %s', 'adf-regional-base-iam'),
        call('Removing stack: %s', 'adf-regional-base-dev'),
        call('Removing stack: %s', 'adf-regional-base-test'),
        call('Removing stack: %s', 'adf-regional-base-acceptance'),
        call('Removing stack: %s', 'adf-regional-base-prod'),
        call(
            'Please remove stack %s manually, state %s implies that it '
            'cannot be deleted automatically',
            'adf-regional-base-some-ou',
            'CREATE_IN_PROGRESS',
        ),
    ])
