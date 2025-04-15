# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
The Jump Role Manager main that is called when ADF is asked to bootstrap an
AWS Account that it has not bootstrapped yet.

This manager is responsible for locking accounts that were bootstrapped before
and granting access to the privileged CrossAccountAccessRole only when we
have not other method to bootstrap/manage the AWS account.

Theory of operation:
    It accesses AWS Organizations and walks through all the accounts that are
    present.

    For each account, it will test if the account is bootstrapped by
    ADF before. It tests this by assuming the Test Bootstrap Role
    (`adf/adf-bootstrap/adf-test-boostrap-role`) in the specific account.
    If that worked, we know that the bootstrap stack is
    present and we should rely on the ADF Bootstrap Update Deployment role
    (`adf/adf-bootstrap/adf-bootstrap-update-deployment-role`).

    If that is not present, we should rely on the CrossAccountAccessRole
    instead.
"""

import ast
import datetime
import json
import math
import os

from aws_xray_sdk.core import patch_all
import boto3
from botocore.exceptions import ClientError

# ADF imports
from logger import configure_logger
from organizations import Organizations
from parameter_store import ParameterStore
from sts import STS

patch_all()

LOGGER = configure_logger(__name__)

ADF_JUMP_MANAGED_POLICY_ARN = os.getenv("ADF_JUMP_MANAGED_POLICY_ARN")
AWS_PARTITION = os.getenv("AWS_PARTITION")
AWS_REGION = os.getenv("AWS_REGION")
CROSS_ACCOUNT_ACCESS_ROLE_NAME = os.getenv("CROSS_ACCOUNT_ACCESS_ROLE_NAME")
DEPLOYMENT_ACCOUNT_ID = os.getenv("DEPLOYMENT_ACCOUNT_ID")
MANAGEMENT_ACCOUNT_ID = os.getenv("MANAGEMENT_ACCOUNT_ID")

# Special accounts are either not considered ever (the management account)
# or are on the priority list to get bootstrapped first (deployment account)
#
# The management account is excluded, as that is not permitted to
# assume with the Cross Account Access Role anyway.
# The deployment account is prioritized as first to bootstrap as all
# other accounts will depend on the resources in the deployment account.
SPECIAL_ACCOUNT_IDS = [
    DEPLOYMENT_ACCOUNT_ID,
    MANAGEMENT_ACCOUNT_ID,
]

ADF_TEST_BOOTSTRAP_ROLE_NAME = "adf/bootstrap/adf-bootstrap-test-role"
MAX_POLICY_VERSIONS = 4
POLICY_VALID_DURATION_IN_HOURS = 2
INCLUDE_NEW_ACCOUNTS_IF_JOINED_IN_LAST_HOURS = 2

MAX_MANAGED_POLICY_LENGTH = 6144
ZERO_ACCOUNTS_POLICY_LENGTH = 265
CHARS_PER_ACCOUNT_ID = 15
MAX_NUMBER_OF_ACCOUNTS = math.floor(
    (
        MAX_MANAGED_POLICY_LENGTH
        - ZERO_ACCOUNTS_POLICY_LENGTH
    )
    / CHARS_PER_ACCOUNT_ID,
)

IAM_CLIENT = boto3.client("iam")
ORGANIZATIONS_CLIENT = boto3.client("organizations")
TAGGING_CLIENT = boto3.client("resourcegroupstaggingapi")
CODEPIPELINE_CLIENT = boto3.client("codepipeline")


def _verify_bootstrap_exists(sts, account_id):
    try:
        sts.assume_cross_account_role(
            (
                f"arn:{AWS_PARTITION}:iam::{account_id}:"
                f"role/{ADF_TEST_BOOTSTRAP_ROLE_NAME}"
            ),
            "jump_role_manager",
        )
        return True
    except ClientError as error:
        LOGGER.debug(
            "Could not assume into %s in %s due to %s",
            ADF_TEST_BOOTSTRAP_ROLE_NAME,
            account_id,
            error,
        )
    return False


def _get_filtered_non_special_root_ou_accounts(
    organizations,
    sts,
    remove_base_in_root,
):
    """
    Get the list of account ids of AWS Accounts in the root OU that were
    bootstrapped by ADF before.

    If the bootstrap stacks need to be removed upon a move of an ADF Account
    to the root of the AWS Organization, i.e. move/to_root/action equals
    either 'remove-base' or 'remove_base', then we should be allowed to use
    the privileged role in root accounts too to remove the bootstrap stacks
    accordingly. As deleting the stacks would also delete the required
    ADF Bootstrap Update Deployment role, hence we cannot perform the action
    with that role. Privileged access is only required to remove the
    bootstrap stacks from those accounts. Hence it should only allow
    privileged access if it is bootstrapped.
    """
    root_ou_accounts = organizations.get_accounts_for_parent(
        organizations.get_ou_root_id(),
    )
    verified_root_ou_accounts = list(map(
        lambda account: {
            **account,
            "Bootstrapped": _verify_bootstrap_exists(
                sts,
                account.get('Id'),
            ),
        },
        filter(
            lambda account: account.get('Id') not in SPECIAL_ACCOUNT_IDS,
            root_ou_accounts,
        ),
    ))

    new_if_joined_since = (
        datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(
            hours=INCLUDE_NEW_ACCOUNTS_IF_JOINED_IN_LAST_HOURS,
        )
    )
    filtered_root_ou_accounts = list(filter(
        lambda account: (
            (
                remove_base_in_root
                # Only allow privileged access to accounts that were
                # bootstrapped so we are allowed to delete the stacks
                and account["Bootstrapped"]
            ) or (
                not account["Bootstrapped"]
                # If it joined recently, we need to be able to bootstrap
                # the account with privileged access
                and account.get('JoinedTimestamp') > new_if_joined_since
            )
        ),
        verified_root_ou_accounts,
    ))
    return filtered_root_ou_accounts


def _get_non_special_adf_accessible_accounts(
    organizations,
    sts,
    protected_ou_ids,
):
    """
    Get the account ids of all AWS Accounts in this AWS Organization,
    with the exception of the accounts that are inactive or located in
    a protected OU.
    """
    adf_accessible_accounts = organizations.get_accounts(
        protected_ou_ids=protected_ou_ids,
        # Exclude accounts that are in the root of the AWS Organization,
        # as these would be retrieved via the
        # _get_adf_bootstrapped_accounts_in_root_ou method.
        include_root=False,
    )
    filtered_adf_accessible_accounts = list(filter(
        # Only allow privileged access to accounts that are NOT bootstrapped
        lambda account: (
            account.get('Id') not in SPECIAL_ACCOUNT_IDS
            and not _verify_bootstrap_exists(sts, account.get('Id'))
        ),
        adf_accessible_accounts,
    ))
    return filtered_adf_accessible_accounts


def _get_non_special_privileged_access_account_ids(
    organizations,
    sts,
    protected_ou_ids,
    include_root,
):
    privileged_access_accounts = (
        _get_non_special_adf_accessible_accounts(
            organizations,
            sts,
            protected_ou_ids,
        )
        + _get_filtered_non_special_root_ou_accounts(
            organizations,
            sts,
            include_root,
        )
    )
    return [
        account.get("Id") for account in privileged_access_accounts
    ]


def _get_non_bootstrapped_accounts(
    organizations,
    sts,
    parameter_store,
):
    protected_ou_ids = ast.literal_eval(
        parameter_store.fetch_parameter_accept_not_found(
            name='protected',
            default_value='[]',
        ),
    )
    move_to_root_action = parameter_store.fetch_parameter_accept_not_found(
        name='moves/to_root/action',
        default_value='safe',
    )
    include_root = move_to_root_action in ['remove-base', 'remove_base']

    optional_deployment_account_first = (
        [] if _verify_bootstrap_exists(sts, DEPLOYMENT_ACCOUNT_ID)
        else [DEPLOYMENT_ACCOUNT_ID]
    )
    sorted_non_bootstrapped_account_ids = list(
        optional_deployment_account_first

        # Sorted list, so we get to bootstrap the accounts in this order too
        + sorted(
            _get_non_special_privileged_access_account_ids(
                organizations,
                sts,
                protected_ou_ids,
                include_root,
            )
        )
    )
    return sorted_non_bootstrapped_account_ids


def _delete_old_policy_versions(iam):
    LOGGER.debug(
        "Checking policy versions for %s",
        ADF_JUMP_MANAGED_POLICY_ARN,
    )
    response = iam.list_policy_versions(
        PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
    )
    if len(response.get('Versions', [])) > MAX_POLICY_VERSIONS:
        LOGGER.debug(
            "Found %d policy versions, which is greater than the defined "
            "maximum of %d. Hence going through the list to select one to "
            "delete.",
            len(response.get('Versions')),
            MAX_POLICY_VERSIONS,
        )

        oldest_version_id = "z"
        for version in response.get('Versions'):
            if version.get('IsDefaultVersion'):
                continue
            oldest_version_id = min(
                oldest_version_id,
                version.get('VersionId', 'z'),
            )

        if oldest_version_id == "z":
            raise RuntimeError(
                "Failed to find the oldest policy in the "
                f"list for {ADF_JUMP_MANAGED_POLICY_ARN}",
            )

        LOGGER.debug(
            "Deleting policy version %s",
            oldest_version_id,
        )
        iam.delete_policy_version(
            PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
            VersionId=oldest_version_id,
        )


def _get_valid_until():
    return (
        (
            datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(hours=POLICY_VALID_DURATION_IN_HOURS)
        )
        .isoformat(timespec='seconds')
        .replace('+00:00', 'Z')
    )


def _generate_empty_policy_document():
    return {
        "Version": "2012-10-17",
        "Statement": [
            # An empty list of statements is not allowed, hence creating
            # a dummy statement that does not have any effect
            {
                "Sid": "EmptyClause",
                "Effect": "Deny",
                "Action": [
                    # sts:AssumeRoleWithWebIdentity is not allowed by the
                    # inline policy of the jump role anyway.
                    # Hence blocking this would not cause any problems.
                    #
                    # It should not deny sts:AssumeRole here, as it might
                    # be granted via the
                    # GrantOrgWidePrivilegedBootstrapAccessFallback
                    # statement
                    "sts:AssumeRoleWithWebIdentity"
                ],
                "Resource": "*",
            }
        ]
    }


def _generate_policy_document(non_bootstrapped_account_ids):
    if not non_bootstrapped_account_ids:
        # If non_bootstrapped_account_ids is empty, it should switch to
        # a meaningless statement instead of stating
        # Condition/StringEquals/aws:ResourceAccount == []
        #
        # If the value it matches against is empty, it will evaluate to True.
        # So an empty list in the condition value evaluates as if the condition
        # is not present. See:
        # https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-reference-policy-checks.html#access-analyzer-reference-policy-checks-suggestion-empty-array-condition
        return _generate_empty_policy_document()
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowNonBootstrappedAccounts",
                "Effect": "Allow",
                "Action": [
                    "sts:AssumeRole"
                ],
                "Resource": [
                    f"arn:{AWS_PARTITION}:iam::*:role/{CROSS_ACCOUNT_ACCESS_ROLE_NAME}",
                ],
                "Condition": {
                    "DateLessThan": {
                        # Setting an end-time to this policy, as this function
                        # is invoked to bootstrap the account. Which hopefully
                        # turned out working. Hence, in the future, the newly
                        # bootstrapped accounts should use only the ADF
                        # Bootstrap Update Deployment role instead.
                        "aws:CurrentTime": _get_valid_until(),
                    },
                    "StringEquals": {
                        "aws:ResourceAccount": non_bootstrapped_account_ids,
                    },
                }
            }
        ]
    }


def _update_managed_policy(iam, non_bootstrapped_account_ids):
    _delete_old_policy_versions(iam)
    iam.create_policy_version(
        PolicyArn=ADF_JUMP_MANAGED_POLICY_ARN,
        PolicyDocument=json.dumps(
            _generate_policy_document(non_bootstrapped_account_ids),
        ),
        SetAsDefault=True,
    )


def _process_update_request(iam, organizations, parameter_store, sts):
    non_bootstrapped_account_ids = _get_non_bootstrapped_accounts(
        organizations,
        sts,
        parameter_store,
    )
    _update_managed_policy(
        iam,
        # Limit the list of account ids to add to the policy to the
        # MAX_NUMBER_OF_ACCOUNTS as more accounts would not fit in
        # a single managed policy. This limit would be 391 accounts.
        # If more accounts need to be bootstrapped, it needs to be performed
        # in multiple iterations. Once they are all bootstrapped, this list
        # will be very small or empty even.
        non_bootstrapped_account_ids[:MAX_NUMBER_OF_ACCOUNTS],
    )
    return {
        "granted_access_to": non_bootstrapped_account_ids[
            :MAX_NUMBER_OF_ACCOUNTS
        ],
        "of_total_non_bootstrapped": len(non_bootstrapped_account_ids),
        "valid_until": (
            _get_valid_until() if non_bootstrapped_account_ids
            else None
        ),
    }


def _build_summary(result):
    number_of_accounts_granted = len(result.get('granted_access_to', []))
    if number_of_accounts_granted:
        return (
            "Task completed. Granted ADF Account-Bootstrapping Jump Role "
            "privileged cross-account access "
            f"to: {number_of_accounts_granted} "
            f"of total {result.get('of_total_non_bootstrapped', 0)} "
            "non-bootstrapped AWS accounts."
            f"Access granted via the {CROSS_ACCOUNT_ACCESS_ROLE_NAME} role "
            f"until {result.get('valid_until')}."
        )
    return (
        "Task completed. The ADF Account-Bootstrapping Jump Role does not "
        "require privileged cross-account access. Access granted to the ADF "
        "Bootstrap Update Deployment role only."
    )


def _report_success_and_log(
    result,
    codepipeline,
    codepipeline_job_id,
    exec_id,
):
    summary = _build_summary(result)
    LOGGER.info(summary)
    if result.get('granted_access_to', []):
        LOGGER.info(
            "Specific accounts that were granted access to: %s",
            ", ".join(result.get('granted_access_to', [])),
        )
    if codepipeline_job_id:
        LOGGER.debug(
            "Reporting success to CodePipeline %s",
            codepipeline_job_id,
        )
        codepipeline.put_job_success_result(
            jobId=codepipeline_job_id,
            executionDetails={
                "externalExecutionId": exec_id,
                "summary": summary,
                "percentComplete": 100,
            }
        )


def _report_failure_and_log(error, codepipeline, codepipeline_job_id, exec_id):
    LOGGER.exception(error)
    summary = (
        "Task failed. Granting the ADF Account-Bootstrapping Jump Role "
        f"privileged cross-account access failed due to an error: {error}."
    )
    LOGGER.error(summary)
    if codepipeline_job_id:
        LOGGER.debug(
            "Reporting failure to CodePipeline %s",
            codepipeline_job_id,
        )
        codepipeline.put_job_failure_result(
            jobId=codepipeline_job_id,
            failureDetails={
                "externalExecutionId": exec_id,
                "type": "JobFailed",
                "message": summary,
            }
        )
    return {
        "error": summary,
    }


def _handle_event(
    iam,
    organizations,
    parameter_store,
    sts,
    codepipeline,
    event,
    exec_id,
):
    codepipeline_job_id = event.get('CodePipeline.job', {}).get('id')
    try:
        result = _process_update_request(
            iam,
            organizations,
            parameter_store,
            sts,
        )
        _report_success_and_log(
            result,
            codepipeline,
            codepipeline_job_id,
            exec_id,
        )
        return {
            **event,
            "grant_access_result": result,
        }
    except ClientError as error:
        return _report_failure_and_log(
            error,
            codepipeline,
            codepipeline_job_id,
            exec_id,
        )


def lambda_handler(event, context):
    organizations = Organizations(
        org_client=ORGANIZATIONS_CLIENT,
        tagging_client=TAGGING_CLIENT,
    )
    parameter_store = ParameterStore(
        region=AWS_REGION,
        role=boto3,
    )
    sts = STS()
    return _handle_event(
        iam=IAM_CLIENT,
        organizations=organizations,
        parameter_store=parameter_store,
        sts=sts,
        codepipeline=CODEPIPELINE_CLIENT,
        event=event,
        exec_id=context.log_stream_name,
    )
