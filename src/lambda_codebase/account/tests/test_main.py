# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import pytest
from mock import patch, call

from main import (
    ensure_account,
    _handle_concurrent_modification,
    _find_deployment_account_via_orgs_api,
    _wait_on_account_creation,
    DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    DEPLOYMENT_OU_PATH,
    SSM_PARAMETER_ADF_DESCRIPTION,
    MAX_RETRIES,
)


class ConcurrentModificationException(Exception):
    pass


class ParameterNotFound(Exception):
    pass


class OtherException(Exception):
    pass


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_given(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = ""

    returned_account_id, created = ensure_account(
        account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=False,
    )

    assert returned_account_id == account_id
    assert not created
    logger.info.assert_has_calls([
        call(
            'Using existing deployment account as specified %s.',
            account_id,
        ),
        call(
            'The %s parameter was not found, creating it',
            DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        ),
    ])
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        Value=account_id,
        Description=SSM_PARAMETER_ADF_DESCRIPTION,
        Type="String",
        Overwrite=True,
    )
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_given_mismatch_ssm_param(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    ssm_account_id = "111111111111"
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": ssm_account_id,
        }
    }
    find_orgs_api.return_value = ""

    with pytest.raises(RuntimeError) as excinfo:
        ensure_account(
            account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
            is_update=False,
        )

    error_message = str(excinfo.value)
    correct_error_message = (
        "Failed to configure the deployment account. "
        f"The {DEPLOYMENT_ACCOUNT_ID_PARAM_PATH} parameter has "
        f"account id {ssm_account_id} configured, while "
        f"the current operation requests using {account_id} "
        "instead. These need to match, if you are sure you want to "
        f"use {account_id}, please update or delete the "
        f"{DEPLOYMENT_ACCOUNT_ID_PARAM_PATH} parameter in AWS Systems "
        "Manager Parameter Store and try again."
    )
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_called_once_with(
        'Using existing deployment account as specified %s.',
        account_id,
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_not_called()
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_given_on_update_no_params(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = account_id

    returned_account_id, created = ensure_account(
        account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=True,
    )

    assert returned_account_id == account_id
    assert not created
    logger.info.assert_has_calls([
        call(
            'Using existing deployment account as specified %s.',
            account_id,
        ),
        call(
            'The %s parameter was not found, creating it',
            DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        ),
    ])
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        Value=account_id,
        Description=SSM_PARAMETER_ADF_DESCRIPTION,
        Type="String",
        Overwrite=True,
    )
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_given_on_update_with_params(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": account_id,
        }
    }
    find_orgs_api.return_value = account_id

    returned_account_id, created = ensure_account(
        account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=True,
    )

    assert returned_account_id == account_id
    assert not created
    logger.info.assert_called_once_with(
        'Using existing deployment account as specified %s.',
        account_id,
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_not_called()
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_found_with_ssm(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": account_id,
        }
    }
    find_orgs_api.return_value = account_id

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=True,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert not created
    logger.info.assert_called_once_with(
        'Using deployment account as specified with param %s : %s.',
        DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        account_id,
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_not_called()
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_not_found_via_orgs_api_on_update(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = account_id

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=True,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert not created
    logger.info.assert_called_once_with(
        "Using deployment account %s as found in AWS Organization %s.",
        account_id,
        DEPLOYMENT_OU_PATH,
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
        Value=account_id,
        Description=SSM_PARAMETER_ADF_DESCRIPTION,
        Type="String",
        Overwrite=True,
    )
    find_orgs_api.assert_called_once_with()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_found_via_orgs_api_on_update(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = ""

    with pytest.raises(RuntimeError) as exc_info:
        ensure_account(
            given_account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
            is_update=True,
        )

    error_msg = (
        "When updating ADF should not be required to create a deployment "
        "account. If your previous installation failed and you try to fix "
        "it via an update, please delete the ADF stack first and run it "
        "as a fresh installation."
    )
    assert str(exc_info.value) == error_msg

    logger.info.assert_not_called()
    logger.error.assert_called_once_with(error_msg)
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name=DEPLOYMENT_ACCOUNT_ID_PARAM_PATH,
    )
    ssm_client.put_parameter.assert_not_called()
    find_orgs_api.assert_called_once_with()
    org_client.create_account.assert_not_called()


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_create_success(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    request_id = "random-request-id"
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = ""
    org_client.create_account.return_value = {
        "CreateAccountStatus": {
            "Id": request_id,
        }
    }
    wait_on_fn.return_value = account_id

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=False,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert created
    logger.info.assert_has_calls(
        [
            call("Creating account ..."),
            call("Account creation requested, request ID: %s", request_id),
        ]
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_called_once_with(request_id)
    ssm_client.get_parameter.assert_called_once_with(
        Name="/adf/deployment_account_id",
    )
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_create_failed_concur(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = ""
    org_client.create_account.side_effect = ConcurrentModificationException(
        "Test",
    )
    concur_mod_fn.return_value = (account_id, True)

    returned_account_id, created = ensure_account(
        given_account_id,
        account_name,
        account_email,
        cross_account_access_role_name,
        is_update=False,
    )

    assert returned_account_id != given_account_id
    assert returned_account_id == account_id
    assert created
    logger.info.assert_has_calls(
        [
            call("Creating account ..."),
        ]
    )
    concur_mod_fn.assert_called_once_with(
        org_client.create_account.side_effect,
        account_name,
        account_email,
        cross_account_access_role_name,
        1,
    )
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name="/adf/deployment_account_id",
    )
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main._find_deployment_account_via_orgs_api")
@patch("main._wait_on_account_creation")
@patch("main._handle_concurrent_modification")
@patch("main.LOGGER")
def test_deployment_account_create_failed_other(
    logger, concur_mod_fn, wait_on_fn, find_orgs_api, ssm_client, org_client
):
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    correct_error_message = "Some other exception"
    ssm_client.exceptions.ParameterNotFound = ParameterNotFound
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )

    ssm_client.get_parameter.side_effect = ParameterNotFound("Test")
    find_orgs_api.return_value = ""
    org_client.create_account.side_effect = OtherException(correct_error_message)

    with pytest.raises(OtherException) as excinfo:
        ensure_account(
            given_account_id,
            account_name,
            account_email,
            cross_account_access_role_name,
            is_update=False,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_has_calls(
        [
            call("Creating account ..."),
        ]
    )
    concur_mod_fn.assert_not_called()
    wait_on_fn.assert_not_called()
    ssm_client.get_parameter.assert_called_once_with(
        Name="/adf/deployment_account_id",
    )
    find_orgs_api.assert_not_called()
    org_client.create_account.assert_called_once_with(
        Email=account_email,
        AccountName=account_name,
        RoleName=cross_account_access_role_name,
        IamUserAccessToBilling="ALLOW",
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.time")
@patch("main.LOGGER")
def test_deployment_account_wait_exception(logger, time_mock, org_client):
    request_id = "random-request-id"
    correct_error_message = "Failed test"
    org_client.describe_create_account_status.side_effect = OtherException(
        correct_error_message
    )

    with pytest.raises(OtherException) as excinfo:
        _wait_on_account_creation(
            request_id,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_not_called()
    time_mock.sleep.assert_not_called()
    org_client.describe_create_account_status.assert_called_once_with(
        CreateAccountRequestId=request_id,
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main.TAGGING_CLIENT")
@patch("main.Organizations")
@patch("main.LOGGER")
def test_deployment_account_find_via_orgs_api_one_found(
    logger, org_cls, tag_client, ssm_client, org_client
):
    account_id = "123456789012"
    org_instance = org_cls.return_value
    org_instance.get_accounts_in_path.return_value = [
        {
            "Id": "111111111111",
            "Status": "SUSPENDED",
        },
        {
            "Id": account_id,
            "Status": "ACTIVE",
        },
        {
            "Id": "111111111111",
            "Status": "PENDING_CLOSURE",
        },
    ]

    returned_account_id = _find_deployment_account_via_orgs_api()

    assert returned_account_id == account_id

    logger.debug.assert_not_called()
    org_cls.assert_called_once_with(
        org_client=org_client,
        tagging_client=tag_client,
    )
    org_instance.get_accounts_in_path.assert_called_once_with(
        DEPLOYMENT_OU_PATH,
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main.TAGGING_CLIENT")
@patch("main.Organizations")
@patch("main.LOGGER")
def test_deployment_account_find_via_orgs_api_none_found(
    logger, org_cls, tag_client, ssm_client, org_client
):
    org_instance = org_cls.return_value
    org_instance.get_accounts_in_path.return_value = [
        {
            "Id": "111111111111",
            "Status": "SUSPENDED",
        },
        {
            "Id": "111111111111",
            "Status": "PENDING_CLOSURE",
        },
    ]

    returned_account_id = _find_deployment_account_via_orgs_api()

    assert returned_account_id == ""

    logger.debug.assert_called_once_with(
        "No active AWS Accounts found in the %s OU path.",
        DEPLOYMENT_OU_PATH,
    )
    org_cls.assert_called_once_with(
        org_client=org_client,
        tagging_client=tag_client,
    )
    org_instance.get_accounts_in_path.assert_called_once_with(
        DEPLOYMENT_OU_PATH,
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.SSM_CLIENT")
@patch("main.TAGGING_CLIENT")
@patch("main.Organizations")
@patch("main.LOGGER")
def test_deployment_account_find_via_orgs_api_multiple_found(
    logger, org_cls, tag_client, ssm_client, org_client
):
    org_instance = org_cls.return_value
    org_instance.get_accounts_in_path.return_value = [
        {
            "Id": "111111111111",
            "Status": "ACTIVE",
        },
        {
            "Id": "222222222222",
            "Status": "ACTIVE",
        },
    ]

    with pytest.raises(RuntimeError) as exc_info:
        _find_deployment_account_via_orgs_api()

    correct_error_message = (
        "Failed to determine Deployment account to setup, as "
        f"2 AWS Accounts were found "
        f"in the {DEPLOYMENT_OU_PATH} organization unit (OU). "
        "Please ensure there is only one account in the "
        f"{DEPLOYMENT_OU_PATH} OU path. "
        "Move all AWS accounts you don't want to be bootstrapped as "
        f"the ADF deployment account out of the {DEPLOYMENT_OU_PATH} "
        "OU. In case there are no accounts in the "
        f"{DEPLOYMENT_OU_PATH} OU, ADF will automatically create a "
        "new AWS account for you, or move the deployment account as "
        "specified at install time of ADF to the respective OU."
    )
    assert str(exc_info.value) == correct_error_message

    logger.debug.assert_not_called()
    org_cls.assert_called_once_with(
        org_client=org_client,
        tagging_client=tag_client,
    )
    org_instance.get_accounts_in_path.assert_called_once_with(
        DEPLOYMENT_OU_PATH,
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.time")
@patch("main.LOGGER")
def test_deployment_account_wait_on_failed(logger, time_mock, org_client):
    request_id = "random-request-id"
    failure_reason = "The failure on create status request"
    org_client.describe_create_account_status.return_value = {
        "CreateAccountStatus": {
            "State": "FAILED",
            "FailureReason": failure_reason,
        }
    }
    correct_error_message = f"Failed to create account because {failure_reason}"

    with pytest.raises(Exception) as excinfo:
        _wait_on_account_creation(
            request_id,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_not_called()
    time_mock.sleep.assert_not_called()
    org_client.describe_create_account_status.assert_called_once_with(
        CreateAccountRequestId=request_id,
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.time")
@patch("main.LOGGER")
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

    returned_account_id = _wait_on_account_creation(
        request_id,
    )

    assert returned_account_id == account_id

    logger.info.assert_has_calls(
        [
            call(
                "Account creation still in progress, waiting.. "
                "then calling again with %s",
                request_id,
            ),
            call("Account created: %s", account_id),
        ]
    )
    time_mock.sleep.assert_called_once_with(10)
    org_client.describe_create_account_status.assert_has_calls(
        [
            call(CreateAccountRequestId=request_id),
            call(CreateAccountRequestId=request_id),
        ]
    )


@patch("main.ORGANIZATION_CLIENT")
@patch("main.ensure_account")
@patch("main.time")
@patch("main.LOGGER")
def test_deployment_account_handle_concurrent_last_try(
    logger, time_mock, ensure_fn, org_client
):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    no_retries = MAX_RETRIES
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )
    correct_error_message = "SomeError"
    err = ConcurrentModificationException(correct_error_message)

    ensure_fn.return_value = (account_id, True)

    returned_account_id, created = _handle_concurrent_modification(
        err,
        account_name,
        account_email,
        cross_account_access_role_name,
        no_retries,
    )

    assert returned_account_id == account_id
    assert created

    logger.info.assert_called_once_with(
        "Attempt %d - hit %s",
        no_retries + 1,
        err,
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


@patch("main.ORGANIZATION_CLIENT")
@patch("main.ensure_account")
@patch("main.time")
@patch("main.LOGGER")
def test_deployment_account_handle_concurrent_too_many_tries(
    logger, time_mock, ensure_fn, org_client
):
    account_id = "123456789012"
    given_account_id = ""
    account_name = "test-deployment-account"
    account_email = "test@amazon.com"
    cross_account_access_role_name = "some-role"
    no_retries = MAX_RETRIES + 1
    org_client.exceptions.ConcurrentModificationException = (
        ConcurrentModificationException
    )
    correct_error_message = "SomeError"
    err = ConcurrentModificationException(correct_error_message)

    ensure_fn.return_value = (account_id, True)

    with pytest.raises(ConcurrentModificationException) as excinfo:
        _handle_concurrent_modification(
            err,
            account_name,
            account_email,
            cross_account_access_role_name,
            no_retries,
        )

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    logger.info.assert_called_once_with(
        "Attempt %d - hit %s",
        no_retries + 1,
        err,
    )
    logger.error.assert_called_once_with(
        "Reached maximum number of retries to create the account. "
        "Raising error to abort the execution."
    )
    time_mock.sleep.assert_not_called()
    ensure_fn.assert_not_called()
