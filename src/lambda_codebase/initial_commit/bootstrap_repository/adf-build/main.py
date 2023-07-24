# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Main entry point for main.py execution which
is executed from within AWS CodeBuild in the management account
"""

import os
import sys
import time
from math import floor
from datetime import datetime
from thread import PropagatingThread

import boto3

from botocore.exceptions import ClientError
from logger import configure_logger
from cache import Cache
from cloudformation import CloudFormation
from parameter_store import ParameterStore
from organizations import Organizations
from stepfunctions import StepFunctions
from errors import GenericAccountConfigureError, ParameterNotFoundError
from sts import STS
from s3 import S3
from partition import get_partition
from config import Config
from organization_policy import OrganizationPolicy


S3_BUCKET_NAME = os.environ["S3_BUCKET"]
REGION_DEFAULT = os.environ["AWS_REGION"]
PARTITION = get_partition(REGION_DEFAULT)
ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]
DEPLOYMENT_ACCOUNT_S3_BUCKET_NAME = os.environ["DEPLOYMENT_ACCOUNT_BUCKET"]
CODEPIPELINE_EXECUTION_ID = os.environ.get("CODEPIPELINE_EXECUTION_ID")
CODEBUILD_START_TIME_UNIXTS = floor(
    int(
        # Returns the unix timestamp in milliseconds
        os.environ.get(
            "CODEBUILD_START_TIME",
            # Fall back to 10 minutes ago + convert Python timestamp from
            # seconds to milliseconds:
            floor(datetime.now().timestamp() - (10 * 60)) * 1000,
        )
    ) / 1000.0  # Convert milliseconds to seconds
)
ACCOUNT_MANAGEMENT_STATE_MACHINE_ARN = os.environ.get(
    "ACCOUNT_MANAGEMENT_STATE_MACHINE_ARN",
)
ACCOUNT_BOOTSTRAPPING_STATE_MACHINE_ARN = os.environ.get(
    "ACCOUNT_BOOTSTRAPPING_STATE_MACHINE_ARN"
)
ADF_DEFAULT_SCM_FALLBACK_BRANCH = 'master'
LOGGER = configure_logger(__name__)


def ensure_generic_account_can_be_setup(sts, config, account_id):
    """
    If the target account has been configured returns the role to assume
    """
    try:
        return sts.assume_cross_account_role(
            f'arn:{PARTITION}:iam::{account_id}:role/'
            f'{config.cross_account_access_role}',
            'base_update'
        )
    except ClientError as error:
        raise GenericAccountConfigureError from error


def update_deployment_account_output_parameters(
        deployment_account_region,
        region,
        kms_and_bucket_dict,
        deployment_account_role,
        cloudformation):
    """
    Update parameters on the deployment account across target
    regions based on the output of CloudFormation base stacks
    in the deployment account.
    """
    deployment_account_parameter_store = ParameterStore(
        deployment_account_region, deployment_account_role
    )
    parameter_store = ParameterStore(
        region, deployment_account_role
    )
    outputs = cloudformation.get_stack_regional_outputs()
    kms_and_bucket_dict[region] = {}
    kms_and_bucket_dict[region]['kms'] = outputs['kms_arn']
    kms_and_bucket_dict[region]['s3_regional_bucket'] = (
        outputs['s3_regional_bucket']
    )
    for key, value in outputs.items():
        deployment_account_parameter_store.put_parameter(
            f"/cross_region/{key}/{region}",
            value
        )
        parameter_store.put_parameter(
            f"/cross_region/{key}/{region}",
            value
        )

    return kms_and_bucket_dict


def prepare_deployment_account(sts, deployment_account_id, config):
    """
    Ensures configuration is up to date on the deployment account
    and returns the role that can be assumed by the management account
    to access the deployment account
    """
    deployment_account_role = sts.assume_cross_account_role(
        f'arn:{PARTITION}:iam::{deployment_account_id}:role/'
        f'{config.cross_account_access_role}',
        'master'
    )
    for region in list(
            set([config.deployment_account_region] + config.target_regions)):
        deployment_account_parameter_store = ParameterStore(
            region,
            deployment_account_role
        )
        deployment_account_parameter_store.put_parameter(
            'organization_id', os.environ["ORGANIZATION_ID"]
        )
        _store_extension_parameters(deployment_account_parameter_store, config)

    deployment_account_parameter_store = ParameterStore(
        config.deployment_account_region,
        deployment_account_role
    )
    deployment_account_parameter_store.put_parameter(
        'adf_version', ADF_VERSION
    )
    deployment_account_parameter_store.put_parameter(
        'adf_log_level', ADF_LOG_LEVEL
    )
    deployment_account_parameter_store.put_parameter(
        'deployment_account_bucket', DEPLOYMENT_ACCOUNT_S3_BUCKET_NAME
    )
    deployment_account_parameter_store.put_parameter(
        'default_scm_branch',
        config.config.get('scm', {}).get(
            'default-scm-branch',
            ADF_DEFAULT_SCM_FALLBACK_BRANCH,
        )
    )
    auto_create_repositories = config.config.get(
        'scm', {}).get('auto-create-repositories')
    if auto_create_repositories is not None:
        deployment_account_parameter_store.put_parameter(
            'auto_create_repositories', str(auto_create_repositories)
        )
    if '@' not in config.notification_endpoint:
        config.notification_channel = config.notification_endpoint
        config.notification_endpoint = (
            f"arn:{PARTITION}:lambda:{config.deployment_account_region}:"
            f"{deployment_account_id}:function:SendSlackNotification"
        )
    for item in (
            'cross_account_access_role',
            'notification_type',
            'notification_endpoint',
            'notification_channel'
    ):
        if getattr(config, item) is not None:
            deployment_account_parameter_store.put_parameter(
                (
                    '/notification_endpoint/main'
                    if item == 'notification_channel'
                    else item
                ),
                str(getattr(config, item))
            )
    _store_extension_parameters(deployment_account_parameter_store, config)

    return deployment_account_role


def _store_extension_parameters(parameter_store, config):
    if not hasattr(config, 'extensions'):
        return

    for extension, attributes in config.extensions.items():
        for attribute in attributes:
            parameter_store.put_parameter(
                f"/adf/extensions/{extension}/{attribute}",
                str(attributes[attribute]),
            )


# pylint: disable=too-many-locals
def worker_thread(
    account_id,
    sts,
    config,
    s3,
    cache,
    updated_kms_bucket_dict
):
    """
    The Worker thread function that is created for each account
    in which CloudFormation create_stack is called
    """
    LOGGER.debug("%s - Starting new worker thread", account_id)

    organizations = Organizations(
        role=boto3,
        account_id=account_id
    )
    ou_id = organizations.get_parent_info().get("ou_parent_id")

    account_path = organizations.build_account_path(
        ou_id,
        [],  # Initial empty array to hold OU Path,
        cache
    )
    try:
        role = ensure_generic_account_can_be_setup(
            sts,
            config,
            account_id
        )

        # Regional base stacks can be updated after global
        all_regions = list(set(
            [config.deployment_account_region]
            + config.target_regions
        ))
        for region in all_regions:
            # Ensuring the kms_arn and bucket_name on the target account is
            # up-to-date
            parameter_store = ParameterStore(region, role)
            parameter_store.put_parameter(
                'kms_arn',
                updated_kms_bucket_dict[region]['kms'],
            )
            parameter_store.put_parameter(
                'bucket_name',
                updated_kms_bucket_dict[region]['s3_regional_bucket'],
            )
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path="adf-bootstrap/" + account_path,
                account_id=account_id
            )
            try:
                cloudformation.create_stack()
                if region == config.deployment_account_region:
                    cloudformation.create_iam_stack()
            except GenericAccountConfigureError as error:
                if 'Unable to fetch parameters' in str(error):
                    LOGGER.error(
                        '%s - Failed to update its base stack due to missing '
                        'parameters (deployment_account_id or kms_arn), '
                        'ensure this account has been bootstrapped correctly '
                        'by being moved from the root into an Organizational '
                        'Unit within AWS Organizations.',
                        account_id,
                    )
                raise LookupError from error

    except GenericAccountConfigureError as generic_account_error:
        LOGGER.info(generic_account_error)
        return


def await_sfn_executions(sfn_client):
    _await_running_sfn_executions(
        sfn_client,
        ACCOUNT_MANAGEMENT_STATE_MACHINE_ARN,
        filter_lambda=lambda item: (
            item.get('name', '').find(CODEPIPELINE_EXECUTION_ID) > 0
        ),
        status_filter='RUNNING',
    )
    _await_running_sfn_executions(
        sfn_client,
        ACCOUNT_BOOTSTRAPPING_STATE_MACHINE_ARN,
        filter_lambda=None,
        status_filter='RUNNING',
    )
    if _sfn_execution_exists_with(
        sfn_client,
        ACCOUNT_MANAGEMENT_STATE_MACHINE_ARN,
        filter_lambda=lambda item: (
            item.get('name', '').find(CODEPIPELINE_EXECUTION_ID) > 0
            and item.get('status') in ['FAILED', 'TIMED_OUT', 'ABORTED']
        ),
        status_filter=None,
    ):
        LOGGER.error(
            "Account Management State Machine encountered a failed, "
            "timed out, or aborted execution. Please look into this problem "
            "before retrying the bootstrap pipeline. You can navigate to: "
            "https://%s.console.aws.amazon.com/states/home?region=%s#/statemachines/view/%s",
            REGION_DEFAULT,
            REGION_DEFAULT,
            ACCOUNT_MANAGEMENT_STATE_MACHINE_ARN,
        )
        sys.exit(1)
    if _sfn_execution_exists_with(
        sfn_client,
        ACCOUNT_BOOTSTRAPPING_STATE_MACHINE_ARN,
        filter_lambda=lambda item: (
            (
                item.get('startDate', datetime.now()).timestamp()
                >= CODEBUILD_START_TIME_UNIXTS
            )
            and item.get('status') in ['FAILED', 'TIMED_OUT', 'ABORTED']
        ),
        status_filter=None,
    ):
        LOGGER.error(
            "Account Bootstrapping State Machine encountered a failed, "
            "timed out, or aborted execution. Please look into this problem "
            "before retrying the bootstrap pipeline. You can navigate to: "
            "https://%(region)s.console.aws.amazon.com/states/home"
            "?region=%(region)s#/statemachines/view/%(sfn_arn)s",
            {
                "region": REGION_DEFAULT,
                "sfn_arn": ACCOUNT_BOOTSTRAPPING_STATE_MACHINE_ARN,
            },
        )
        sys.exit(2)


def _await_running_sfn_executions(
    sfn_client,
    sfn_arn,
    filter_lambda,
    status_filter,
):
    while _sfn_execution_exists_with(
        sfn_client,
        sfn_arn,
        filter_lambda,
        status_filter
    ):
        LOGGER.info(
            "Waiting for 30 seconds for the executions of %s to finish.",
            sfn_arn,
        )
        time.sleep(30)


def _sfn_execution_exists_with(
    sfn_client,
    sfn_arn,
    filter_lambda,
    status_filter,
):
    request_params = {
        "stateMachineArn": sfn_arn,
    }
    if status_filter:
        request_params["statusFilter"] = status_filter

    paginator = sfn_client.get_paginator('list_executions')
    for page in paginator.paginate(**request_params):
        filtered = (
            list(filter(filter_lambda, page["executions"])) if filter_lambda
            else page["executions"]
        )
        if filtered:
            LOGGER.info(
                "Found %d state machine %s that %s running.",
                len(filtered),
                "executions" if len(filtered) > 1 else "execution",
                "are" if len(filtered) > 1 else "is",
            )
            return True

    return False


def main():  # pylint: disable=R0915
    LOGGER.info("ADF Version %s", ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    await_sfn_executions(boto3.client('stepfunctions'))

    policies = OrganizationPolicy()
    config = Config()

    try:
        parameter_store = ParameterStore(REGION_DEFAULT, boto3)
        deployment_account_id = parameter_store.fetch_parameter(
            'deployment_account_id'
        )
        organizations = Organizations(
            role=boto3,
            account_id=deployment_account_id
        )
        policies.apply(organizations, parameter_store, config.config)
        sts = STS()
        deployment_account_role = prepare_deployment_account(
            sts=sts,
            deployment_account_id=deployment_account_id,
            config=config
        )

        cache = Cache()
        ou_id = organizations.get_parent_info().get("ou_parent_id")
        account_path = organizations.build_account_path(
            ou_id=ou_id,
            account_path=[],
            cache=cache
        )
        s3 = S3(
            region=REGION_DEFAULT,
            bucket=S3_BUCKET_NAME
        )

        kms_and_bucket_dict = {}
        # First Setup/Update the Deployment Account in all regions (KMS Key and
        # S3 Bucket + Parameter Store values)
        regions_to_enable = list(
            set(
                [config.deployment_account_region]
                + config.target_regions
            )
        )
        for region in regions_to_enable:
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=deployment_account_role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path="adf-bootstrap/" + account_path,
                account_id=deployment_account_id
            )
            cloudformation.create_stack()
            update_deployment_account_output_parameters(
                deployment_account_region=config.deployment_account_region,
                region=region,
                kms_and_bucket_dict=kms_and_bucket_dict,
                deployment_account_role=deployment_account_role,
                cloudformation=cloudformation
            )
            if region == config.deployment_account_region:
                cloudformation.create_iam_stack()

        # Updating the stack on the management account in deployment region
        cloudformation = CloudFormation(
            region=config.deployment_account_region,
            deployment_account_region=config.deployment_account_region,
            role=boto3,
            wait=True,
            stack_name=None,
            s3=s3,
            s3_key_path='adf-build',
            account_id=ACCOUNT_ID
        )
        cloudformation.create_stack()
        threads = []
        account_ids = [
            account_id["Id"]
            for account_id in organizations.get_accounts(
                protected_ou_ids=config.config.get('protected'),
                include_root=False,
            )
        ]
        non_deployment_account_ids = [
            account for account in account_ids
            if account != deployment_account_id
        ]
        for account_id in non_deployment_account_ids:
            thread = PropagatingThread(target=worker_thread, args=(
                account_id,
                sts,
                config,
                s3,
                cache,
                kms_and_bucket_dict
            ))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        LOGGER.info("Executing Step Function on Deployment Account")
        step_functions = StepFunctions(
            role=deployment_account_role,
            deployment_account_id=deployment_account_id,
            deployment_account_region=config.deployment_account_region,
            regions=config.target_regions,
            account_ids=account_ids,
            update_pipelines_only=0
        )

        step_functions.execute_statemachine()
    except ParameterNotFoundError:
        LOGGER.info(
            'A Deployment Account is ready to be bootstrapped! '
            'The Account provisioner will now kick into action, '
            'be sure to check out its progress in AWS Step Functions '
            'in this account.'
        )
        return


if __name__ == '__main__':
    main()
