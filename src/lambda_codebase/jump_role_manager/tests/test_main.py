# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import datetime
import json
from unittest.mock import Mock, patch, call

import pytest
from botocore.exceptions import ClientError

from aws_xray_sdk import global_sdk_config
from main import (
    ADF_JUMP_MANAGED_POLICY_ARN,
    ADF_TEST_BOOTSTRAP_ROLE_NAME,
    CROSS_ACCOUNT_ACCESS_ROLE_NAME,
    INCLUDE_NEW_ACCOUNTS_IF_JOINED_IN_LAST_HOURS,
    MAX_NUMBER_OF_ACCOUNTS,
    MAX_POLICY_VERSIONS,
    POLICY_VALID_DURATION_IN_HOURS,
    _build_summary,
    _delete_old_policy_versions,
    _generate_policy_document,
    _get_non_bootstrapped_accounts,
    _get_valid_until,
    _handle_event,
    _process_update_request,
    _report_failure_and_log,
    _report_success_and_log,
    _update_managed_policy,
    _verify_bootstrap_exists,
)


@pytest.fixture
def mock_codepipeline():
    return Mock()


@pytest.fixture
def mock_iam():
    return Mock()


@pytest.fixture
def mock_sts():
    return Mock()


@pytest.fixture
def mock_parameter_store():
    mock_parameter_store = Mock()
    mock_parameter_store.fetch_parameter_accept_not_found.side_effect = [
        "['ou1', 'ou2']",
        "safe",
    ]
    return mock_parameter_store


@pytest.fixture
def mock_organizations():
    return Mock()
# ---------------------------------------------------------


def test_max_number_of_accounts():
    assert MAX_NUMBER_OF_ACCOUNTS == 391


def test_max_policy_versions():
    assert MAX_POLICY_VERSIONS > 1
    assert MAX_POLICY_VERSIONS < 6


def test_policy_valid_duration_in_hours():
    assert POLICY_VALID_DURATION_IN_HOURS > 0
    assert POLICY_VALID_DURATION_IN_HOURS < 4
# ---------------------------------------------------------


@patch("main._report_failure_and_log")
@patch("main._report_success_and_log")
@patch("main._process_update_request")
def test_handle_event_success(
    process_mock,
    report_success_mock,
    report_failure_mock,
    mock_codepipeline,
    mock_iam,
    mock_sts,
    mock_parameter_store,
    mock_organizations,
):
    """
    Test _handle_event with a successful execution
    """
    event = {
        "CodePipeline.job": {
            "id": "cp-id",
        },
    }
    process_result = "The Result"
    exec_id = "some-exec-id",
    process_mock.return_value = process_result

    result = _handle_event(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
        mock_codepipeline,
        event,
        exec_id,
    )

    assert result == {
        **event,
        "grant_access_result": process_result,
    }

    process_mock.assert_called_once_with(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
    )
    report_success_mock.assert_called_once_with(
        process_result,
        mock_codepipeline,
        "cp-id",
        exec_id,
    )
    report_failure_mock.assert_not_called()


@patch("main._report_failure_and_log")
@patch("main._report_success_and_log")
@patch("main._process_update_request")
def test_handle_event_failure(
    process_mock,
    report_success_mock,
    report_failure_mock,
    mock_codepipeline,
    mock_iam,
    mock_sts,
    mock_parameter_store,
    mock_organizations,
):
    """
    Test _handle_event with a failed execution
    """
    event = {
        "CodePipeline.job": {
            "id": "cp-id",
        },
    }
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied'}},
        operation_name='SomeOperation'
    )
    exec_id = "some-exec-id",
    process_mock.side_effect = error

    _handle_event(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
        mock_codepipeline,
        event,
        exec_id,
    )

    process_mock.assert_called_once_with(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
    )
    report_success_mock.assert_not_called()
    report_failure_mock.assert_called_once_with(
        error,
        mock_codepipeline,
        "cp-id",
        exec_id,
    )
# ---------------------------------------------------------


@patch('main.LOGGER')
@patch('main._build_summary')
def test_report_success_and_log_no_privileged_access_sfn(
    summary_mock,
    logger,
    mock_codepipeline,
):
    result = {
        "granted_access_to": [],
        "of_total_non_bootstrapped": 0,
        "valid_until": None,
    }
    summary = 'The summary'
    summary_mock.return_value = summary

    _report_success_and_log(
        result,
        mock_codepipeline,
        None,
        'some-exec-id',
    )

    summary_mock.assert_called_once_with(result)
    logger.info.assert_called_once_with(summary)
    logger.debug.assert_not_called()

    mock_codepipeline.put_job_success_result.assert_not_called()
    mock_codepipeline.put_job_failure_result.assert_not_called()


@patch('main.LOGGER')
@patch('main._build_summary')
def test_report_success_and_log_with_privileged_access_sfn(
    summary_mock,
    logger,
    mock_codepipeline,
):
    result = {
        "granted_access_to": ['111111111111', '222222222222'],
        "of_total_non_bootstrapped": 3,
        "valid_until": '2024-04-03T14:00:00Z',
    }
    summary = 'The summary'
    summary_mock.return_value = summary

    _report_success_and_log(
        result,
        mock_codepipeline,
        None,
        'some-exec-id',
    )

    summary_mock.assert_called_once_with(result)
    logger.info.assert_has_calls([
        call(summary),
        call(
            "Specific accounts that were granted access to: %s",
            "111111111111, 222222222222",
        ),
    ])
    logger.debug.assert_not_called()

    mock_codepipeline.put_job_success_result.assert_not_called()
    mock_codepipeline.put_job_failure_result.assert_not_called()


@patch('main.LOGGER')
@patch('main._build_summary')
def test_report_success_and_log_no_privileged_access_codepipeline(
    summary_mock,
    logger,
    mock_codepipeline,
):
    result = {
        "granted_access_to": [],
        "of_total_non_bootstrapped": 0,
        "valid_until": None,
    }
    summary = 'The summary'
    summary_mock.return_value = summary

    _report_success_and_log(
        result,
        mock_codepipeline,
        'cp-id',
        'some-exec-id',
    )

    summary_mock.assert_called_once_with(result)
    logger.info.assert_called_once_with(summary)
    logger.debug.assert_called_once_with(
        "Reporting success to CodePipeline %s",
        "cp-id",
    )

    mock_codepipeline.put_job_success_result.assert_called_once_with(
        jobId="cp-id",
        executionDetails={
            "externalExecutionId": "some-exec-id",
            "summary": summary,
            "percentComplete": 100,
        },
    )
    mock_codepipeline.put_job_failure_result.assert_not_called()


@patch('main.LOGGER')
@patch('main._build_summary')
def test_report_success_and_log_with_privileged_access_codepipeline(
    summary_mock,
    logger,
    mock_codepipeline,
):
    result = {
        "granted_access_to": ['111111111111', '222222222222'],
        "of_total_non_bootstrapped": 3,
        "valid_until": '2024-04-03T14:00:00Z',
    }
    summary = 'The summary'
    summary_mock.return_value = summary

    _report_success_and_log(
        result,
        mock_codepipeline,
        'cp-id',
        'some-exec-id',
    )

    summary_mock.assert_called_once_with(result)
    logger.info.assert_has_calls([
        call(summary),
        call(
            "Specific accounts that were granted access to: %s",
            "111111111111, 222222222222",
        ),
    ])
    logger.debug.assert_called_once_with(
        "Reporting success to CodePipeline %s",
        "cp-id",
    )

    mock_codepipeline.put_job_success_result.assert_called_once_with(
        jobId="cp-id",
        executionDetails={
            "externalExecutionId": "some-exec-id",
            "summary": summary,
            "percentComplete": 100,
        },
    )
    mock_codepipeline.put_job_failure_result.assert_not_called()
# ---------------------------------------------------------


@patch('main.LOGGER')
def test_report_failure_and_log_sfn(
    logger,
    mock_codepipeline,
):
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied'}},
        operation_name='SomeOperation'
    )
    summary = (
        "Task failed. Granting the ADF Account-Bootstrapping Jump Role "
        f"privileged cross-account access failed due to an error: {error}."
    )

    result = _report_failure_and_log(
        error,
        mock_codepipeline,
        None,
        'some-exec-id',
    )

    assert result == {
        "error": summary,
    }

    logger.error.assert_called_once_with(summary)
    logger.debug.assert_not_called()

    mock_codepipeline.put_job_success_result.assert_not_called()
    mock_codepipeline.put_job_failure_result.assert_not_called()


@patch('main.LOGGER')
@patch('main._build_summary')
def test_report_failure_and_log_codepipeline(
    summary_mock,
    logger,
    mock_codepipeline,
):
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied'}},
        operation_name='SomeOperation'
    )
    summary = (
        "Task failed. Granting the ADF Account-Bootstrapping Jump Role "
        f"privileged cross-account access failed due to an error: {error}."
    )

    result = _report_failure_and_log(
        error,
        mock_codepipeline,
        'cp-id',
        'some-exec-id',
    )

    assert result == {
        "error": summary,
    }

    logger.error.assert_called_once_with(summary)
    logger.debug.assert_called_once_with(
        "Reporting failure to CodePipeline %s",
        "cp-id",
    )

    mock_codepipeline.put_job_success_result.assert_not_called()
    mock_codepipeline.put_job_failure_result.assert_called_once_with(
        jobId="cp-id",
        failureDetails={
            "externalExecutionId": "some-exec-id",
            "type": "JobFailed",
            "message": summary,
        },
    )
# ---------------------------------------------------------


def test_build_summary_no_privileged_access():
    result = {
        "granted_access_to": [],
        "of_total_non_bootstrapped": 0,
        "valid_until": None,
    }

    summary = _build_summary(result)

    assert summary == (
        "Task completed. The ADF Account-Bootstrapping Jump Role does not "
        "require privileged cross-account access. Access granted to the ADF "
        "Bootstrap Update Deployment role only."
    )


def test_build_summary_with_privileged_access():
    result = {
        "granted_access_to": ['111111111111', '222222222222'],
        "of_total_non_bootstrapped": 3,
        "valid_until": '2024-04-03T14:00:00Z',
    }

    summary = _build_summary(result)

    assert summary == (
        "Task completed. Granted ADF Account-Bootstrapping Jump Role "
        "privileged cross-account access to: 2 "
        "of total 3 non-bootstrapped AWS accounts."
        f"Access granted via the {CROSS_ACCOUNT_ACCESS_ROLE_NAME} role "
        "until 2024-04-03T14:00:00Z."
    )


# ---------------------------------------------------------


@patch("main._get_valid_until")
@patch("main._update_managed_policy")
@patch("main._get_non_bootstrapped_accounts")
def test_process_update_request_no_non_bootstrapped_accounts(
    get_mock,
    update_mock,
    valid_until_mock,
    mock_iam,
    mock_sts,
    mock_parameter_store,
    mock_organizations,
):
    """
    Test case when there are no non-bootstrapped accounts
    """
    get_mock.return_value = []

    result = _process_update_request(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
    )

    assert result == {
        "granted_access_to": [],
        "of_total_non_bootstrapped": 0,
        "valid_until": None,
    }

    get_mock.assert_called_once_with(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )
    update_mock.assert_called_once_with(
        mock_iam,
        [],
    )
    valid_until_mock.assert_not_called()


@patch("main._get_valid_until")
@patch("main._update_managed_policy")
@patch("main._get_non_bootstrapped_accounts")
def test_process_update_request_with_non_bootstrapped_accounts(
    get_mock,
    update_mock,
    valid_until_mock,
    mock_iam,
    mock_sts,
    mock_parameter_store,
    mock_organizations,
):
    """
    Test case when there are non-bootstrapped accounts
    """
    non_bootstrapped_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
    ]
    valid_until = '2024-04-03T14:00:00Z'
    valid_until_mock.return_value = valid_until
    get_mock.return_value = non_bootstrapped_account_ids

    result = _process_update_request(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
    )

    assert result == {
        "granted_access_to": non_bootstrapped_account_ids,
        "of_total_non_bootstrapped": len(non_bootstrapped_account_ids),
        "valid_until": valid_until,
    }

    get_mock.assert_called_once_with(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )
    update_mock.assert_called_once_with(
        mock_iam,
        get_mock.return_value,
    )
    valid_until_mock.assert_called_once_with()


@patch("main._get_valid_until")
@patch("main._update_managed_policy")
@patch("main._get_non_bootstrapped_accounts")
def test_process_update_request_with_more_non_bootstrapped_accounts_than_max(
    get_mock,
    update_mock,
    valid_until_mock,
    monkeypatch,
    mock_iam,
    mock_sts,
    mock_parameter_store,
    mock_organizations,
):
    """
    Test case when there are more non-bootstrapped accounts than the
    configured MAX_NUMBER_OF_ACCOUNTS
    """
    non_bootstrapped_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
    ]
    get_mock.return_value = non_bootstrapped_account_ids
    valid_until = '2024-04-03T14:00:00Z'
    valid_until_mock.return_value = valid_until
    monkeypatch.setattr('main.MAX_NUMBER_OF_ACCOUNTS', 2)

    result = _process_update_request(
        mock_iam,
        mock_organizations,
        mock_parameter_store,
        mock_sts,
    )

    assert result == {
        "granted_access_to": non_bootstrapped_account_ids[:2],
        "of_total_non_bootstrapped": len(non_bootstrapped_account_ids),
        "valid_until": valid_until,
    }

    get_mock.assert_called_once_with(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )
    update_mock.assert_called_once_with(
        mock_iam,
        ['111111111111', '222222222222'],
    )
    valid_until_mock.assert_called_once_with()
# ---------------------------------------------------------


@patch("main._delete_old_policy_versions")
@patch("main._generate_policy_document")
def test_update_managed_policy(gen_mock, del_mock, mock_iam):
    non_bootstrapped_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
    ]
    gen_mock.return_value = {
        "Some": "Policy Doc",
    }
    _update_managed_policy(mock_iam, non_bootstrapped_account_ids)

    del_mock.assert_called_once_with(mock_iam)
    mock_iam.create_policy_version.assert_called_once_with(
        PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
        PolicyDocument=json.dumps(
            gen_mock.return_value,
        ),
        SetAsDefault=True,
    )
# ---------------------------------------------------------


@patch('main.datetime')
def test_get_valid_until(dt_mock):
    mock_utc_now = datetime.datetime(2024, 4, 3, 12, 0, 0, tzinfo=datetime.UTC)
    dt_mock.datetime.now.return_value = mock_utc_now
    dt_mock.timedelta.return_value = datetime.timedelta(
        hours=POLICY_VALID_DURATION_IN_HOURS,
    )
    # Shifted by 2 hours due to shift of POLICY_VALID_DURATION_IN_HOURS
    expected_end_time = '2024-04-03T14:00:00Z'
    assert _get_valid_until() == expected_end_time


@patch('main.datetime')
def test_get_valid_until_valid_duration(dt_mock):
    mock_utc_now = datetime.datetime(2024, 4, 3, 12, 0, 0, tzinfo=datetime.UTC)
    dt_mock.datetime.now.return_value = mock_utc_now
    dt_mock.timedelta.return_value = datetime.timedelta(
        hours=POLICY_VALID_DURATION_IN_HOURS,
    )

    expected_duration = datetime.timedelta(
        hours=POLICY_VALID_DURATION_IN_HOURS,
    )
    end_time = datetime.datetime.fromisoformat(
        _get_valid_until().replace('Z', '+00:00'),
    )
    assert end_time - mock_utc_now == expected_duration
# ---------------------------------------------------------


@patch("main._get_valid_until")
def test_generate_policy_document_no_accounts_to_bootstrap(get_mock):
    end_time = '2024-04-03T14:00:00Z'
    get_mock.return_value = end_time
    non_bootstrapped_account_ids = []
    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EmptyClause",
                "Effect": "Deny",
                "Action": ["sts:AssumeRoleWithWebIdentity"],
                "Resource": "*",
            }
        ]
    }

    policy = _generate_policy_document(non_bootstrapped_account_ids)
    assert policy == expected_policy


@patch("main._get_valid_until")
def test_generate_policy_document(get_mock):
    end_time = '2024-04-03T14:00:00Z'
    get_mock.return_value = end_time
    non_bootstrapped_account_ids = [
        '111111111111',
        '222222222222',
        '333333333333',
    ]
    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowNonBootstrappedAccounts",
                "Effect": "Allow",
                "Action": ["sts:AssumeRole"],
                "Resource": [
                    f"arn:aws:iam::*:role/{CROSS_ACCOUNT_ACCESS_ROLE_NAME}",
                ],
                "Condition": {
                    "DateLessThan": {
                        "aws:CurrentTime": end_time,
                    },
                    "StringEquals": {
                        "aws:ResourceAccount": non_bootstrapped_account_ids,
                    },
                }
            }
        ]
    }

    policy = _generate_policy_document(non_bootstrapped_account_ids)
    assert policy == expected_policy
# ---------------------------------------------------------


def test_delete_old_policy_versions_below_max(mock_iam):
    mock_iam.list_policy_versions.return_value = {
        "Versions": [
            {"VersionId": "v1", "IsDefaultVersion": True},
            {"VersionId": "v2", "IsDefaultVersion": False},
            {"VersionId": "v3", "IsDefaultVersion": False},
        ]
    }

    _delete_old_policy_versions(mock_iam)

    mock_iam.delete_policy_version.assert_not_called()


@patch('main.LOGGER')
def test_delete_old_policy_versions_above_max(logger, mock_iam):
    mock_iam.list_policy_versions.return_value = {
        "Versions": [
            {"VersionId": "v1", "IsDefaultVersion": True},
            {"VersionId": "v2", "IsDefaultVersion": False},
            {"VersionId": "v3", "IsDefaultVersion": False},
            {"VersionId": "v4", "IsDefaultVersion": False},
            {"VersionId": "v5", "IsDefaultVersion": False},
        ]
    }

    _delete_old_policy_versions(mock_iam)

    mock_iam.delete_policy_version.assert_called_once_with(
        PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
        VersionId="v2",
    )
    logger.debug.assert_has_calls([
        call("Checking policy versions for %s", ADF_JUMP_MANAGED_POLICY_ARN),
        call(
            "Found %d policy versions, which is greater than the defined "
            "maximum of %d. Hence going through the list to select one "
            "to delete.",
            5,
            4,
        ),
        call("Deleting policy version %s", "v2"),
    ])


@patch('main.LOGGER')
def test_delete_old_policy_versions_above_max_out_of_order(logger, mock_iam):
    mock_iam.list_policy_versions.return_value = {
        "Versions": [
            {"VersionId": "v2", "IsDefaultVersion": False},
            {"VersionId": "v3", "IsDefaultVersion": False},
            {"VersionId": "v1", "IsDefaultVersion": True},
            {"VersionId": "v4", "IsDefaultVersion": False},
            {"VersionId": "v5", "IsDefaultVersion": False},
        ]
    }

    _delete_old_policy_versions(mock_iam)

    mock_iam.delete_policy_version.assert_called_once_with(
        PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
        VersionId="v2",
    )
    logger.debug.assert_has_calls([
        call("Checking policy versions for %s", ADF_JUMP_MANAGED_POLICY_ARN),
        call(
            "Found %d policy versions, which is greater than the defined "
            "maximum of %d. Hence going through the list to select one "
            "to delete.",
            5,
            4,
        ),
        call("Deleting policy version %s", "v2"),
    ])


@patch('main.LOGGER')
def test_delete_old_policy_versions_should_never_happen(logger, mock_iam):
    mock_iam.list_policy_versions.return_value = {
        "Versions": [
            {"IsDefaultVersion": False},
            {"IsDefaultVersion": False},
            {"IsDefaultVersion": True},
            {"IsDefaultVersion": False},
            {"IsDefaultVersion": False},
        ]
    }

    with pytest.raises(RuntimeError) as excinfo:
        _delete_old_policy_versions(mock_iam)

    correct_error_message = (
        "Failed to find the oldest policy in the "
        f"list for {ADF_JUMP_MANAGED_POLICY_ARN}"
    )
    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    mock_iam.delete_policy_version.assert_not_called()
    logger.debug.assert_has_calls([
        call("Checking policy versions for %s", ADF_JUMP_MANAGED_POLICY_ARN),
        call(
            "Found %d policy versions, which is greater than the defined "
            "maximum of %d. Hence going through the list to select one "
            "to delete.",
            5,
            4,
        ),
    ])
# ---------------------------------------------------------


@patch("main._verify_bootstrap_exists")
def test_get_non_bootstrapped_accounts_no_accounts(
    verify_mock,
    mock_organizations,
    mock_sts,
    mock_parameter_store,
    monkeypatch,
):
    # Mock the organizations.get_accounts function to return an empty list
    mock_organizations.get_accounts.return_value = []
    management_account_id = '999999999999'
    deployment_account_id = '888888888888'
    verify_mock.side_effect = (
        lambda sts, account_id: account_id == deployment_account_id
    )

    mock_organizations.get_ou_root_id.return_value = 'r-123'
    mock_organizations.get_accounts_for_parent.return_value = []
    monkeypatch.setattr('main.MANAGEMENT_ACCOUNT_ID', management_account_id)
    monkeypatch.setattr('main.DEPLOYMENT_ACCOUNT_ID', deployment_account_id)
    monkeypatch.setattr('main.SPECIAL_ACCOUNT_IDS', [
        management_account_id,
        deployment_account_id,
    ])

    # Call the function with mocked inputs
    result = _get_non_bootstrapped_accounts(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )

    assert not result
    mock_organizations.get_accounts.assert_called_once_with(
        protected_ou_ids=['ou1', 'ou2'],
        include_root=False,
    )
    verify_mock.assert_called_once_with(
        mock_sts,
        deployment_account_id,
    )
    mock_parameter_store.fetch_parameter_accept_not_found.assert_has_calls([
        call(name='protected', default_value='[]'),
        call(name='moves/to_root/action', default_value='safe')
    ])


@patch("main._verify_bootstrap_exists")
def test_get_non_bootstrapped_accounts_only_deployment_account(
    verify_mock,
    mock_organizations,
    mock_sts,
    mock_parameter_store,
    monkeypatch,
):
    management_account_id = '999999999999'
    deployment_account_id = '888888888888'
    mock_organizations.get_accounts.return_value = [
        {
            "Id": deployment_account_id,
        },
    ]
    verify_mock.side_effect = (
        lambda sts, account_id: account_id != deployment_account_id
    )

    mock_organizations.get_ou_root_id.return_value = 'r-123'
    mock_organizations.get_accounts_for_parent.return_value = []
    monkeypatch.setattr('main.MANAGEMENT_ACCOUNT_ID', management_account_id)
    monkeypatch.setattr('main.DEPLOYMENT_ACCOUNT_ID', deployment_account_id)
    monkeypatch.setattr('main.SPECIAL_ACCOUNT_IDS', [
        management_account_id,
        deployment_account_id,
    ])

    # Call the function with mocked inputs
    result = _get_non_bootstrapped_accounts(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )

    assert [deployment_account_id] == result
    mock_organizations.get_accounts.assert_called_once_with(
        protected_ou_ids=['ou1', 'ou2'],
        include_root=False,
    )
    verify_mock.assert_called_once_with(
        mock_sts,
        deployment_account_id,
    )


@patch("main._verify_bootstrap_exists")
def test_get_non_bootstrapped_accounts_all_bootstrapped(
    verify_mock,
    mock_organizations,
    mock_sts,
    mock_parameter_store,
    monkeypatch,
):
    management_account_id = '999999999999'
    deployment_account_id = '888888888888'
    # Mock the organizations.get_accounts function to return an empty list
    mock_organizations.get_accounts.return_value = list(map(
        lambda account_id: {
            "Id": account_id,
        },
        [
            management_account_id,
            '333333333333',
            deployment_account_id,
            '111111111111',
            '222222222222',
        ],
    ))
    verify_mock.return_value = True

    mock_organizations.get_ou_root_id.return_value = 'r-123'
    mock_organizations.get_accounts_for_parent.return_value = []
    monkeypatch.setattr('main.MANAGEMENT_ACCOUNT_ID', management_account_id)
    monkeypatch.setattr('main.DEPLOYMENT_ACCOUNT_ID', deployment_account_id)
    monkeypatch.setattr('main.SPECIAL_ACCOUNT_IDS', [
        management_account_id,
        deployment_account_id,
    ])

    # Call the function with mocked inputs
    result = _get_non_bootstrapped_accounts(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )

    assert not result
    mock_organizations.get_accounts.assert_called_once_with(
        protected_ou_ids=['ou1', 'ou2'],
        include_root=False,
    )
    verify_mock.assert_has_calls(
        [
            call(mock_sts, deployment_account_id),
            call(mock_sts, '111111111111'),
            call(mock_sts, '222222222222'),
            call(mock_sts, '333333333333'),
        ],
        any_order=True,
    )


@patch("main._verify_bootstrap_exists")
def test_get_non_bootstrapped_accounts_none_bootstrapped(
    verify_mock,
    mock_organizations,
    mock_sts,
    mock_parameter_store,
    monkeypatch,
):
    management_account_id = '999999999999'
    deployment_account_id = '888888888888'
    # Mock the organizations.get_accounts function to return an empty list
    mock_organizations.get_accounts.return_value = list(map(
        lambda account_id: {
            "Id": account_id,
        },
        [
            management_account_id,
            '333333333333',
            deployment_account_id,
            '111111111111',
            '222222222222',
        ],
    ))
    protected_ou_ids = ['ou1', 'ou2']
    verify_mock.return_value = False

    mock_organizations.get_ou_root_id.return_value = 'r-123'
    mock_organizations.get_accounts_for_parent.return_value = []
    monkeypatch.setattr('main.MANAGEMENT_ACCOUNT_ID', management_account_id)
    monkeypatch.setattr('main.DEPLOYMENT_ACCOUNT_ID', deployment_account_id)
    monkeypatch.setattr('main.SPECIAL_ACCOUNT_IDS', [
        management_account_id,
        deployment_account_id,
    ])

    # Call the function with mocked inputs
    result = _get_non_bootstrapped_accounts(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )

    assert result == [
        # In this specific order:
        deployment_account_id,
        '111111111111',
        '222222222222',
        '333333333333',
    ]
    mock_organizations.get_accounts.assert_called_once_with(
        protected_ou_ids=protected_ou_ids,
        include_root=False,
    )
    verify_mock.assert_has_calls(
        [
            call(mock_sts, deployment_account_id),
            call(mock_sts, '111111111111'),
            call(mock_sts, '222222222222'),
            call(mock_sts, '333333333333'),
        ],
        any_order=True,
    )


@pytest.mark.parametrize(
    "move_action, include_root",
    [
        pytest.param("remove-base", True),
        pytest.param("remove_base", True),
        pytest.param("safe", False),
        pytest.param(None, False),
        pytest.param("", False),
        pytest.param("other", False),
    ]
)
@patch("main._verify_bootstrap_exists")
def test_get_non_bootstrapped_accounts_include_root(
    verify_mock,
    move_action,
    include_root,
    mock_organizations,
    mock_sts,
    mock_parameter_store,
    monkeypatch,
):
    mock_parameter_store.fetch_parameter_accept_not_found = Mock()
    mock_parameter_store.fetch_parameter_accept_not_found.side_effect = [
        "['ou1', 'ou2']",
        move_action,
    ]
    management_account_id = '999999999999'
    deployment_account_id = '888888888888'
    some_non_bootstrapped_root_ou_account_id = '111111111111'
    new_non_bootstrapped_root_ou_account_id = '666666666666'
    bootstrapped_root_ou_account_id = '444444444444'
    root_ou_id = 'r-abc'
    new_account_joined_date = (
        datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(
            hours=INCLUDE_NEW_ACCOUNTS_IF_JOINED_IN_LAST_HOURS,
        )
        + datetime.timedelta(
            minutes=1,
        )
    )
    old_account_joined_date = (
        datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(
            hours=INCLUDE_NEW_ACCOUNTS_IF_JOINED_IN_LAST_HOURS,
            minutes=1,
        )
    )
    mock_organizations.get_ou_root_id.return_value = root_ou_id
    mock_organizations.get_accounts_for_parent.return_value = list(map(
        lambda account_id: {
            "Id": account_id,
            "JoinedTimestamp": (
                old_account_joined_date
                if account_id == some_non_bootstrapped_root_ou_account_id
                else new_account_joined_date
            ),
        },
        [
            some_non_bootstrapped_root_ou_account_id,
            new_non_bootstrapped_root_ou_account_id,
            bootstrapped_root_ou_account_id,
        ],
    ))
    # Mock the organizations.get_accounts function to return an empty list
    mock_organizations.get_accounts.return_value = list(map(
        lambda account_id: {
            "Id": account_id,
        },
        [
            management_account_id,
            '333333333333',
            deployment_account_id,
            '555555555555',
            '222222222222',
        ],
    ))
    protected_ou_ids = ['ou1', 'ou2']
    boostrapped_account_ids = [
        bootstrapped_root_ou_account_id,
        '555555555555',
    ]
    verify_mock.side_effect = lambda _, x: x in boostrapped_account_ids

    monkeypatch.setattr('main.MANAGEMENT_ACCOUNT_ID', management_account_id)
    monkeypatch.setattr('main.DEPLOYMENT_ACCOUNT_ID', deployment_account_id)
    monkeypatch.setattr('main.SPECIAL_ACCOUNT_IDS', [
        management_account_id,
        deployment_account_id,
    ])

    # Call the function with mocked inputs
    result = _get_non_bootstrapped_accounts(
        mock_organizations,
        mock_sts,
        mock_parameter_store,
    )

    expected_result = [
        # In this specific order:
        deployment_account_id,
        '222222222222',
        '333333333333',
    ]
    if include_root:
        expected_result.append(bootstrapped_root_ou_account_id)
    expected_result.append(new_non_bootstrapped_root_ou_account_id)
    assert result == expected_result

    mock_organizations.get_accounts.assert_called_once_with(
        protected_ou_ids=protected_ou_ids,
        include_root=False,
    )
    mock_organizations.get_ou_root_id.assert_called_once_with()
    mock_organizations.get_accounts_for_parent.assert_called_once_with(
        root_ou_id,
    )

    verify_call_list = [
        call(mock_sts, deployment_account_id),
        call(mock_sts, '222222222222'),
        call(mock_sts, '333333333333'),
        call(mock_sts, '555555555555'),
        call(mock_sts, new_non_bootstrapped_root_ou_account_id),
    ]
    if include_root:
        verify_call_list.append(
            call(mock_sts, some_non_bootstrapped_root_ou_account_id),
        )
        verify_call_list.append(
            call(mock_sts, bootstrapped_root_ou_account_id),
        )
    verify_mock.assert_has_calls(verify_call_list, any_order=True)
# ---------------------------------------------------------


@patch('main.LOGGER')
def test_verify_bootstrap_exists_success(logger, mock_sts):
    # Mocking the successful case
    mock_sts.assume_cross_account_role.return_value = {}

    assert _verify_bootstrap_exists(mock_sts, '111111111111')
    logger.debug.assert_not_called()


@patch('main.LOGGER')
def test_verify_bootstrap_exists_failure(logger, mock_sts):
    account_id = '111111111111'
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied'}},
        operation_name='AssumeRole'
    )
    mock_sts.assume_cross_account_role.side_effect = error

    assert not _verify_bootstrap_exists(mock_sts, account_id)
    logger.debug.assert_called_once_with(
        "Could not assume into %s in %s due to %s",
        ADF_TEST_BOOTSTRAP_ROLE_NAME,
        account_id,
        error,
    )
