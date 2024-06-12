# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""Tests for sts.py"""

# pylint: skip-file

import pytest
import boto3
from botocore.exceptions import ClientError

from unittest.mock import Mock, patch, call
from sts import (
    ADF_JUMP_ROLE_NAME,
    ADF_BOOTSTRAP_UPDATE_DEPLOYMENT_ROLE_NAME,
    STS,
)


def build_mocked_sts_client_success(identifier=""):
    sts_client = Mock()
    sts_client.assume_role.return_value = build_success_assume_role_response(
        identifier,
    )
    return sts_client


def build_success_assume_role_response(identifier):
    return {
        "Credentials": {
            "AccessKeyId": f"ak{identifier}",
            "SecretAccessKey": f"sak{identifier}",
            "SessionToken": f"st{identifier}",
        },
    }


@pytest.fixture
def sts_client():
    return Mock()


@patch("sts.LOGGER")
def test_assume_cross_account_role(logger):
    sts_client = build_mocked_sts_client_success()
    sts = STS(sts_client)
    role_arn = "arn:aws:iam::123456789012:role/test-role"
    role_session_name = "test-session"

    session = sts.assume_cross_account_role(role_arn, role_session_name)

    assert isinstance(session, boto3.Session)
    assert session.get_credentials().access_key == "ak"
    assert session.get_credentials().secret_key == "sak"
    assert session.get_credentials().token == "st"

    logger.debug.assert_called_once_with(
        "Assuming into %s with session name: %s",
        role_arn,
        role_session_name,
    )
    logger.info.assert_called_once_with(
        "Assumed into %s with session name: %s",
        role_arn,
        role_session_name,
    )

    sts_client.assume_role.assert_called_once_with(
        RoleArn=role_arn,
        RoleSessionName=role_session_name,
    )
# ---------------------------------------------------------


def test_build_role_arn():
    role_arn = STS._build_role_arn(
        partition="aws",
        account_id="123456789012",
        role_name="test-role",
    )
    assert role_arn == "arn:aws:iam::123456789012:role/test-role"
# ---------------------------------------------------------


@patch("sts.boto3")
@patch("sts.LOGGER")
def test_assume_bootstrap_deployment_role_privileged_allowed(logger, boto_mock):
    root_sts_client = build_mocked_sts_client_success('-jump')
    jump_session_mock = Mock()
    deploy_session_mock = Mock()
    boto_mock.Session.side_effect = [
        jump_session_mock,
        deploy_session_mock,
    ]

    jump_session_sts_client = build_mocked_sts_client_success('-privileged')
    jump_session_mock.client.return_value = jump_session_sts_client

    sts = STS(root_sts_client)
    partition = "aws"
    management_account_id = '999999999999'
    account_id = "123456789012"
    privileged_role_name = "test-privileged-role"
    role_session_name = "test-session"

    session = sts.assume_bootstrap_deployment_role(
        partition,
        management_account_id,
        account_id,
        privileged_role_name,
        role_session_name,
    )

    assert session == deploy_session_mock

    boto_mock.Session.assert_has_calls([
        call(
            aws_access_key_id="ak-jump",
            aws_secret_access_key="sak-jump",
            aws_session_token="st-jump",
        ),
        call(
            aws_access_key_id="ak-privileged",
            aws_secret_access_key="sak-privileged",
            aws_session_token="st-privileged",
        ),
    ])
    assert boto_mock.Session.call_count == 2

    jump_role_arn = STS._build_role_arn(
        partition,
        management_account_id,
        ADF_JUMP_ROLE_NAME,
    )
    privileged_role_arn = STS._build_role_arn(
        partition,
        account_id,
        privileged_role_name,
    )
    logger.debug.assert_has_calls([
        call(
            "Assuming into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            privileged_role_arn,
            role_session_name,
        ),
    ])
    assert logger.debug.call_count == 2
    logger.info.assert_has_calls([
        call(
            "Using ADF Account-Bootstrapping Jump Role to assume into "
            "account %s",
            account_id,
        ),
        call(
            "Assumed into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assumed into %s with session name: %s",
            privileged_role_arn,
            role_session_name,
        ),
    ])
    assert logger.info.call_count == 3
    logger.warning.assert_called_once_with(
        "Using the privileged cross-account access role: %s, "
        "as access to this role was granted for account %s",
        privileged_role_name,
        account_id,
    )

    root_sts_client.assume_role.assert_called_once_with(
        RoleArn=jump_role_arn,
        RoleSessionName=role_session_name,
    )

    jump_session_sts_client.assume_role.assert_called_once_with(
        RoleArn=privileged_role_arn,
        RoleSessionName=role_session_name,
    )


@patch("sts.boto3")
@patch("sts.LOGGER")
def test_assume_bootstrap_deployment_other_error(logger, boto_mock):
    root_sts_client = build_mocked_sts_client_success('-jump')
    jump_session_mock = Mock()
    deploy_session_mock = Mock()
    boto_mock.Session.side_effect = [
        jump_session_mock,
        deploy_session_mock,
    ]

    jump_session_sts_client = Mock()
    # Throw an Unknown error when it tried to access the privileged
    # cross-account access role.
    error = ClientError(
        error_response={'Error': {'Code': 'Unknown'}},
        operation_name='AssumeRole'
    )
    jump_session_sts_client.assume_role.side_effect = error
    jump_session_mock.client.return_value = jump_session_sts_client

    sts = STS(root_sts_client)
    partition = "aws"
    management_account_id = '999999999999'
    account_id = "123456789012"
    privileged_role_name = "test-privileged-role"
    role_session_name = "test-session"

    with pytest.raises(ClientError):
        sts.assume_bootstrap_deployment_role(
            partition,
            management_account_id,
            account_id,
            privileged_role_name,
            role_session_name,
        )

    boto_mock.Session.assert_has_calls([
        call(
            aws_access_key_id="ak-jump",
            aws_secret_access_key="sak-jump",
            aws_session_token="st-jump",
        ),
    ])
    assert boto_mock.Session.call_count == 1

    jump_role_arn = STS._build_role_arn(
        partition,
        management_account_id,
        ADF_JUMP_ROLE_NAME,
    )
    privileged_role_arn = STS._build_role_arn(
        partition,
        account_id,
        privileged_role_name,
    )
    logger.debug.assert_has_calls([
        call(
            "Assuming into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            privileged_role_arn,
            role_session_name,
        ),
    ])
    assert logger.debug.call_count == 2
    logger.info.assert_has_calls([
        call(
            "Using ADF Account-Bootstrapping Jump Role to assume into "
            "account %s",
            account_id,
        ),
        call(
            "Assumed into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
    ])
    assert logger.info.call_count == 2
    logger.warning.assert_not_called()

    root_sts_client.assume_role.assert_called_once_with(
        RoleArn=jump_role_arn,
        RoleSessionName=role_session_name,
    )

    jump_session_sts_client.assume_role.assert_called_once_with(
        RoleArn=privileged_role_arn,
        RoleSessionName=role_session_name,
    )


@patch("sts.boto3")
@patch("sts.LOGGER")
def test_assume_bootstrap_deployment_role_privileged_access_denied(
    logger,
    boto_mock,
):
    root_sts_client = build_mocked_sts_client_success('-jump')
    jump_session_mock = Mock()
    deploy_session_mock = Mock()
    boto_mock.Session.side_effect = [
        jump_session_mock,
        deploy_session_mock,
    ]

    jump_session_sts_client = Mock()
    jump_session_sts_client.assume_role.side_effect = [
        # Throw an Access Denied error when it tried to access the
        # privileged cross-account access role.
        ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='AssumeRole'
        ),
        # Accept the request for the ADF Bootstrap Update Deployment Role.
        build_success_assume_role_response(
            '-deploy',
        ),
    ]
    jump_session_mock.client.return_value = jump_session_sts_client

    sts = STS(root_sts_client)
    partition = "aws"
    management_account_id = '999999999999'
    account_id = "123456789012"
    privileged_role_name = "test-privileged-role"
    role_session_name = "test-session"

    session = sts.assume_bootstrap_deployment_role(
        partition,
        management_account_id,
        account_id,
        privileged_role_name,
        role_session_name,
    )

    assert session == deploy_session_mock

    boto_mock.Session.assert_has_calls([
        call(
            aws_access_key_id="ak-jump",
            aws_secret_access_key="sak-jump",
            aws_session_token="st-jump",
        ),
        call(
            aws_access_key_id="ak-deploy",
            aws_secret_access_key="sak-deploy",
            aws_session_token="st-deploy",
        ),
    ])
    assert boto_mock.Session.call_count == 2

    jump_role_arn = STS._build_role_arn(
        partition,
        management_account_id,
        ADF_JUMP_ROLE_NAME,
    )
    privileged_role_arn = STS._build_role_arn(
        partition,
        account_id,
        privileged_role_name,
    )
    deploy_role_arn = STS._build_role_arn(
        partition,
        account_id,
        ADF_BOOTSTRAP_UPDATE_DEPLOYMENT_ROLE_NAME,
    )
    logger.debug.assert_has_calls([
        call(
            "Assuming into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            privileged_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            deploy_role_arn,
            role_session_name,
        ),
    ])
    assert logger.debug.call_count == 3
    logger.info.assert_has_calls([
        call(
            "Using ADF Account-Bootstrapping Jump Role to assume into "
            "account %s",
            account_id,
        ),
        call(
            "Assumed into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assumed into %s with session name: %s",
            deploy_role_arn,
            role_session_name,
        ),
    ])
    assert logger.info.call_count == 3
    logger.warning.assert_not_called()

    root_sts_client.assume_role.assert_called_once_with(
        RoleArn=jump_role_arn,
        RoleSessionName=role_session_name,
    )

    jump_session_sts_client.assume_role.assert_has_calls([
        call(
            RoleArn=privileged_role_arn,
            RoleSessionName=role_session_name,
        ),
        call(
            RoleArn=deploy_role_arn,
            RoleSessionName=role_session_name,
        ),
    ])
    assert jump_session_sts_client.assume_role.call_count == 2


@patch("sts.boto3")
@patch("sts.LOGGER")
def test_assume_bootstrap_deployment_role_deployment_access_denied_too(
    logger,
    boto_mock,
):
    root_sts_client = build_mocked_sts_client_success('-jump')
    jump_session_mock = Mock()
    deploy_session_mock = Mock()
    boto_mock.Session.side_effect = [
        jump_session_mock,
        deploy_session_mock,
    ]

    jump_session_sts_client = Mock()
    jump_session_sts_client.assume_role.side_effect = [
        # Throw an Access Denied error when it tried to access the
        # privileged cross-account access role.
        ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='AssumeRole'
        ),
        # Throw an Access Denied error when it tried to access the
        # ADF Bootstrap Update Deployment Role
        ClientError(
            error_response={'Error': {'Code': 'AccessDenied'}},
            operation_name='AssumeRole'
        ),
    ]
    jump_session_mock.client.return_value = jump_session_sts_client

    sts = STS(root_sts_client)
    partition = "aws"
    management_account_id = '999999999999'
    account_id = "123456789012"
    privileged_role_name = "test-privileged-role"
    role_session_name = "test-session"

    with pytest.raises(ClientError):
        sts.assume_bootstrap_deployment_role(
            partition,
            management_account_id,
            account_id,
            privileged_role_name,
            role_session_name,
        )

    boto_mock.Session.assert_has_calls([
        call(
            aws_access_key_id="ak-jump",
            aws_secret_access_key="sak-jump",
            aws_session_token="st-jump",
        ),
    ])
    assert boto_mock.Session.call_count == 1

    jump_role_arn = STS._build_role_arn(
        partition,
        management_account_id,
        ADF_JUMP_ROLE_NAME,
    )
    privileged_role_arn = STS._build_role_arn(
        partition,
        account_id,
        privileged_role_name,
    )
    deploy_role_arn = STS._build_role_arn(
        partition,
        account_id,
        ADF_BOOTSTRAP_UPDATE_DEPLOYMENT_ROLE_NAME,
    )
    logger.debug.assert_has_calls([
        call(
            "Assuming into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            privileged_role_arn,
            role_session_name,
        ),
        call(
            "Assuming into %s with session name: %s",
            deploy_role_arn,
            role_session_name,
        ),
    ])
    assert logger.debug.call_count == 3
    logger.info.assert_has_calls([
        call(
            "Using ADF Account-Bootstrapping Jump Role to assume into "
            "account %s",
            account_id,
        ),
        call(
            "Assumed into %s with session name: %s",
            jump_role_arn,
            role_session_name,
        ),
    ])
    assert logger.info.call_count == 2
    logger.warning.assert_not_called()

    root_sts_client.assume_role.assert_called_once_with(
        RoleArn=jump_role_arn,
        RoleSessionName=role_session_name,
    )

    jump_session_sts_client.assume_role.assert_has_calls([
        call(
            RoleArn=privileged_role_arn,
            RoleSessionName=role_session_name,
        ),
        call(
            RoleArn=deploy_role_arn,
            RoleSessionName=role_session_name,
        ),
    ])
    assert jump_session_sts_client.assume_role.call_count == 2
