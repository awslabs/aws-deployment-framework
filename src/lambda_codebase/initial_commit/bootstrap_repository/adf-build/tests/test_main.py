# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os

from pytest import fixture
from parameter_store import ParameterStore
from mock import MagicMock, Mock, patch, call
from main import (
    Config,
    ensure_generic_account_can_be_setup,
    prepare_deployment_account,
    update_deployment_account_output_parameters,
)


@fixture
def cls():
    parameter_store = Mock()
    config = Config(
        parameter_store=parameter_store,
        config_path='{0}/stubs/stub_adfconfig.yml'.format(
            os.path.dirname(os.path.realpath(__file__))
        )
    )
    return config


@fixture
def sts():
    sts = Mock()

    role_mock = Mock()
    role_mock.client = Mock()
    role_mock.Credentials = {
        'AccessKeyId': 'string',
        'SecretAccessKey': 'string',
        'SessionToken': 'string',
        'Expiration': 12345
    }
    role_mock.AssumedRoleUser = {
        'AssumedRoleId': 'string',
        'Arn': 'string'
    }
    sts.assume_cross_account_role.return_value = role_mock
    sts.assume_bootstrap_deployment_role.return_value = role_mock
    return sts


def test_ensure_generic_account_can_be_setup(cls, sts):
    assert ensure_generic_account_can_be_setup(sts, cls, '123456789012') == (
        sts.assume_cross_account_role()
    )


def test_update_deployment_account_output_parameters(cls, sts):
    cloudformation = Mock()
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    cloudformation.get_stack_regional_outputs.return_value = {
        "kms_arn": 'some_kms_arn',
        "s3_regional_bucket": 'some_s3_bucket'
    }
    with patch.object(ParameterStore, 'put_parameter') as mock:
        expected_calls = [
            call(
                'cross_region/kms_arn/eu-central-1',
                'some_kms_arn',
            ),
            call(
                'cross_region/s3_regional_bucket/eu-central-1',
                'some_s3_bucket',
            ),
        ]
        update_deployment_account_output_parameters(
            deployment_account_region='eu-central-1',
            region='eu-central-1',
            deployment_account_role=sts,
            kms_and_bucket_dict={},
            cloudformation=cloudformation
        )
        assert 6 == mock.call_count
        mock.assert_has_calls(expected_calls, any_order=True)


@patch('main.ParameterStore')
def test_prepare_deployment_account_defaults(param_store_cls, cls, sts):
    deploy_param_store = MagicMock()
    parameter_stores = {
        'eu-central-1': deploy_param_store,
        'eu-west-1': MagicMock(),
        'us-west-2': MagicMock(),
    }
    parameter_store_list = [
        deploy_param_store,
        parameter_stores['eu-west-1'],
        parameter_stores['us-west-2'],
    ]
    param_store_cls.side_effect = [
        parameter_stores['eu-west-1'],
        parameter_stores['us-west-2'],
        deploy_param_store,
        deploy_param_store,
    ]
    deployment_account_id = "111122223333"
    prepare_deployment_account(
        sts=sts,
        deployment_account_id=deployment_account_id,
        config=cls,
    )
    assert param_store_cls.call_count == 4
    param_store_cls.assert_has_calls(
        [
            call(
                'eu-central-1',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'eu-west-1',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'us-west-2',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'eu-central-1',
                sts.assume_cross_account_role.return_value,
            ),
        ],
        any_order=False,
    )
    for param_store in parameter_store_list:
        assert param_store.put_parameter.call_count == (
            15 if param_store == deploy_param_store else 9
        )
        param_store.put_parameter.assert_has_calls(
            [
                call('adf_version', '1.0.0'),
                call('adf_log_level', 'CRITICAL'),
                call('cross_account_access_role', 'some_role'),
                call(
                    'shared_modules_bucket',
                    'some_shared_modules_bucket',
                ),
                call('bootstrap_templates_bucket', 'some_bucket'),
                call('deployment_account_id', deployment_account_id),
                call('management_account_id', '123'),
                call('organization_id', 'o-123456789'),
                call('extensions/terraform/enabled', 'False'),
            ],
            any_order=False,
        )
    deploy_param_store.put_parameter.assert_has_calls(
        [
            call('adf_version', '1.0.0'),
            call('adf_log_level', 'CRITICAL'),
            call('cross_account_access_role', 'some_role'),
            call('shared_modules_bucket', 'some_shared_modules_bucket'),
            call('bootstrap_templates_bucket', 'some_bucket'),
            call('deployment_account_id', '111122223333'),
            call('management_account_id', '123'),
            call('organization_id', 'o-123456789'),
            call('extensions/terraform/enabled', 'False'),
            call('scm/default_scm_branch', 'main'),
            call('scm/default_scm_codecommit_account_id', '111122223333'),
            call('deployment_maps/allow_empty_target', 'disabled'),
            call('org/stage', 'none'),
            call('notification_type', 'email'),
            call('notification_endpoint', 'john@example.com')],
        any_order=True,
    )


@patch('main.ParameterStore')
def test_prepare_deployment_account_specific_config(param_store_cls, cls, sts):
    deploy_param_store = MagicMock()
    parameter_stores = {
        'eu-central-1': deploy_param_store,
        'eu-west-1': MagicMock(),
        'us-west-2': MagicMock(),
    }
    parameter_store_list = [
        deploy_param_store,
        parameter_stores['eu-west-1'],
        parameter_stores['us-west-2'],
    ]
    param_store_cls.side_effect = [
        parameter_stores['eu-west-1'],
        parameter_stores['us-west-2'],
        deploy_param_store,
        deploy_param_store,
    ]
    deployment_account_id = "111122223333"
    # Set optional config
    cls.notification_type = 'slack'
    cls.notification_endpoint = 'slack-channel'
    cls.notification_channel = 'slack-channel'
    cls.config['scm'] = {
        'auto-create-repositories': 'disabled',
        'default-scm-branch': 'main',
    }
    cls.extensions['terraform'] = {
        'enabled': 'True',
    }
    cls.config['org'] = {
        'stage': 'test-stage',
    }
    cls.config['deployment-maps'] = {
        'allow-empty-target': 'disabled',
    }
    prepare_deployment_account(
        sts=sts,
        deployment_account_id=deployment_account_id,
        config=cls,
    )
    assert param_store_cls.call_count == 4
    param_store_cls.assert_has_calls(
        [
            call(
                'eu-central-1',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'eu-west-1',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'us-west-2',
                sts.assume_cross_account_role.return_value,
            ),
            call(
                'eu-central-1',
                sts.assume_cross_account_role.return_value,
            ),
        ],
        any_order=False,
    )
    for param_store in parameter_store_list:
        assert param_store.put_parameter.call_count == (
            18 if param_store == deploy_param_store else 9
        )
        param_store.put_parameter.assert_has_calls(
            [
                call('adf_version', '1.0.0'),
                call('adf_log_level', 'CRITICAL'),
                call('cross_account_access_role', 'some_role'),
                call(
                    'shared_modules_bucket',
                    'some_shared_modules_bucket',
                ),
                call('bootstrap_templates_bucket', 'some_bucket'),
                call('deployment_account_id', deployment_account_id),
                call('management_account_id', '123'),
                call('organization_id', 'o-123456789'),
                call('extensions/terraform/enabled', 'True'),
            ],
            any_order=False,
        )
    deploy_param_store.put_parameter.assert_has_calls(
        [
            call('adf_version', '1.0.0'),
            call('adf_log_level', 'CRITICAL'),
            call('cross_account_access_role', 'some_role'),
            call('shared_modules_bucket', 'some_shared_modules_bucket'),
            call('bootstrap_templates_bucket', 'some_bucket'),
            call('deployment_account_id', '111122223333'),
            call('management_account_id', '123'),
            call('organization_id', 'o-123456789'),
            call('extensions/terraform/enabled', 'True'),
            call('scm/auto_create_repositories', 'disabled'),
            call('scm/default_scm_branch', 'main'),
            call('scm/default_scm_codecommit_account_id', '111122223333'),
            call('deployment_maps/allow_empty_target', 'disabled'),
            call('org/stage', 'test-stage'),
            call('auto_create_repositories', 'disabled'),
            call('notification_type', 'slack'),
            call('notification_endpoint', 'arn:aws:lambda:eu-central-1:111122223333:function:SendSlackNotification'),
            call('notification_endpoint/main', 'slack-channel')
                ],
        any_order=False,
    )
