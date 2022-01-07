# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import pytest
from mock import patch, call
from main import (
    ensure_account, handle_concurrent_modification, wait_on_account_creation,
    MAX_RETRIES,
)


class ConcurrentModificationException(Exception):
    pass


class ParameterNotFound(Exception):
    pass


class OtherException(Exception):
    pass


@patch('main.ORGANIZATION_CLIENT')
@patch('main.SSM_CLIENT')
@patch('main.wait_on_account_creation')
@patch('main.handle_concurrent_modification')
@patch('main.LOGGER')
def test_deployment_account_given(logger, concur_mod_fn, wait_on_fn,
                                  ssm_client, org_client):
    account_id = "123456789012"
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException

    returned_account_id, created = ensure_account(
        account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
    )

    assert returned_account_id == account_id
    assert not created
    logger.info.assert_not_called()
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_not_called()
    org_client.create_account.assert_not_called()


@patch('main.ORGANIZATION_CLIENT')
@patch('main.SSM_CLIENT')
@patch('main.wait_on_account_creation')
@patch('main.handle_concurrent_modification')
@patch('main.LOGGER')
def test_deployment_account_found_with_ssm(logger, concur_mod_fn, wait_on_fn,
                                           ssm_client, org_client):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException

    ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": account_id,
        }
    }

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert not created
    logger.info.assert_not_called()
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name="deployment_account_id",
    )
    org_client.create_account.assert_not_called()


@patch('main.ORGANIZATION_CLIENT')
@patch('main.SSM_CLIENT')
@patch('main.wait_on_account_creation')
@patch('main.handle_concurrent_modification')
@patch('main.LOGGER')
def test_deployment_account_create_success(logger, concur_mod_fn, wait_on_fn,
                                           ssm_client, org_client):
    request_id = "random-request-id"
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    org_client.create_account.return_value = {
        'CreateAccountStatus': {
            'Id': request_id,
        }
    }
    wait_on_fn.return_value = (account_id, True)

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert created
    logger.info.assert_has_calls([
        call("Creating account ..."),
        call("Account creation requested, request ID: %s", request_id),
    ])
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_called_once_with(request_id)
    ssm_client.get_parameter.assert_called_once_with(
        Name="deployment_account_id",
    )
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.SSM_CLIENT')
@patch('main.wait_on_account_creation')
@patch('main.handle_concurrent_modification')
@patch('main.LOGGER')
def test_deployment_account_create_failed_concur(logger, concur_mod_fn,
                                                 wait_on_fn, ssm_client,
                                                 org_client):
    request_id = "random-request-id"
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    org_client.create_account.side_effect = ConcurrentModificationException(
        "Test",
    )
    concur_mod_fn.return_value = (account_id, True)

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert created
    logger.info.assert_has_calls([
        call("Creating account ..."),
    ])
    concur_mod_fn.assert_called_once_with(
        org_client.create_account.side_effect,
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        1,
    )
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name="deployment_account_id",
    )
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.SSM_CLIENT')
@patch('main.wait_on_account_creation')
@patch('main.handle_concurrent_modification')
@patch('main.LOGGER')
def test_deployment_account_create_failed_other(logger, concur_mod_fn,
                                                wait_on_fn, ssm_client,
                                                org_client):
    request_id = "random-request-id"
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    correct_error_message = "Some other exception"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    org_client.create_account.side_effect = \
        OtherException(correct_error_message)

    with pytest.raises(OtherException) as excinfo:
        ensure_account(
            given_account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_has_calls([
        call("Creating account ..."),
    ])
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name="deployment_account_id",
    )
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.time')
@patch('main.LOGGER')
def test_deployment_account_wait_exception(logger, time_mock, org_client):
    request_id = "random-request-id"
    correct_error_message = "Failed test"
    org_client.describe_create_account_status.side_effect = \
        OtherException(correct_error_message)

    with pytest.raises(OtherException) as excinfo:
        wait_on_account_creation(
            request_id,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_not_called()
    time_mock.sleep.assert_not_called()
    org_client.describe_create_account_status.assert_called_once_with(
        CreateAccountRequestId=request_id,
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.time')
@patch('main.LOGGER')
def test_deployment_account_wait_on_failed(logger, time_mock, org_client):
    request_id = "random-request-id"
    failure_reason = "The failure on create status request"
    org_client.describe_create_account_status.return_value = {
        "CreateAccountStatus": {
            "State": "FAILED",
            "FailureReason": failure_reason,
        }
    }
    correct_error_message = \
        "Failed to create account because %s" % failure_reason

    with pytest.raises(Exception) as excinfo:
        wait_on_account_creation(
            request_id,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_not_called()
    time_mock.sleep.assert_not_called()
    org_client.describe_create_account_status.assert_called_once_with(
        CreateAccountRequestId=request_id,
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.time')
@patch('main.LOGGER')
def test_deployment_account_wait_in_progress_success(logger, time_mock, org_client):
    request_id = "random-request-id"
    account_id = "123456789012"
    org_client.describe_create_account_status.side_effect = [
        {
            "CreateAccountStatus": {
                "State": "IN_PROGRESS",
            }
        },
        {
            "CreateAccountStatus": {
                "State": "SUCCEEDED",
                "AccountId": account_id,
            }
        },
    ]

    returned_account_id, created = wait_on_account_creation(
        request_id,
    )

    assert returned_account_id == account_id
    assert created

    logger.info.assert_has_calls([
        call(
            "Account creation still in progress, waiting.. "
            "then calling again with %s",
            request_id,
        ),
        call("Account created: %s", account_id)
    ])
    time_mock.sleep.assert_called_once_with(10)
    org_client.describe_create_account_status.assert_has_calls([
        call(CreateAccountRequestId=request_id),
        call(CreateAccountRequestId=request_id),
    ])


@patch('main.ORGANIZATION_CLIENT')
@patch('main.ensure_account')
@patch('main.time')
@patch('main.LOGGER')
def test_deployment_account_handle_concurrent_last_try(logger, time_mock,
                                                    ensure_fn, org_client):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    no_retries = MAX_RETRIES
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException
    correct_error_message = "SomeError"
    err = ConcurrentModificationException(correct_error_message)

    ensure_fn.return_value = (account_id, True)

    returned_account_id, created = handle_concurrent_modification(
        err,
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        no_retries,
    )

    assert returned_account_id == account_id
    assert created

    logger.info.assert_called_once_with(
        "Attempt %d - hit %s", no_retries + 1, err,
    )
    logger.error.assert_not_called()
    time_mock.sleep.assert_called_once_with(5)
    ensure_fn.assert_called_once_with(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        no_retries + 1,
    )


@patch('main.ORGANIZATION_CLIENT')
@patch('main.ensure_account')
@patch('main.time')
@patch('main.LOGGER')
def test_deployment_account_handle_concurrent_too_many_tries(logger,
                                                             time_mock,
                                                             ensure_fn,
                                                             org_client):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    no_retries = MAX_RETRIES + 1
    org_client.exceptions.ConcurrentModificationException = \
        ConcurrentModificationException
    correct_error_message = "SomeError"
    err = ConcurrentModificationException(correct_error_message)

    ensure_fn.return_value = (account_id, True)

    with pytest.raises(ConcurrentModificationException) as excinfo:
        handle_concurrent_modification(
            err,
            given_account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
            no_retries,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_called_once_with(
        "Attempt %d - hit %s", no_retries + 1, err,
    )
    logger.error.assert_called_once_with(
        "Reached maximum number of retries to create the account. "
        "Raising error to abort the execution."
    )
    time_mock.sleep.assert_not_called()
    ensure_fn.assert_not_called()
