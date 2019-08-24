# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Main entry point for main.py execution which
is executed from within AWS CodeBuild in the Master Account
"""

import os
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
from config import Config
from scp import SCP


S3_BUCKET_NAME = os.environ["S3_BUCKET"]
REGION_DEFAULT = os.environ["AWS_REGION"]
ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]
DEPLOYMENT_ACCOUNT_S3_BUCKET_NAME = os.environ["DEPLOYMENT_ACCOUNT_BUCKET"]
LOGGER = configure_logger(__name__)


def is_account_in_invalid_state(ou_id, config):
    """
    Check if Account is sitting in the root
    of the Organization or in Protected OU
    """
    if ou_id.startswith('r-'):
        return "Is in the Root of the Organization, it will be skipped."

    protected = config.get('protected', [])
    if ou_id in protected:
        return "Is a in a protected Organizational Unit {0}, it will be skipped.".format(ou_id)

    return False


def ensure_generic_account_can_be_setup(sts, config, account_id):
    """
    If the target account has been configured returns the role to assume
    """
    try:
        return sts.assume_cross_account_role(
            'arn:aws:iam::{0}:role/{1}'.format(
                account_id,
                config.cross_account_access_role),
            'base_update'
        )
    except ClientError as error:
        raise GenericAccountConfigureError from error


def update_deployment_account_output_parameters(
        deployment_account_region,
        region,
        kms_dict,
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
    kms_dict[region] = outputs['kms_arn']
    for key, value in outputs.items():
        deployment_account_parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )
        parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )

    return kms_dict


def prepare_deployment_account(sts, deployment_account_id, config):
    """
    Ensures configuration is up to date on the deployment account
    and returns the role that can be assumed by the master account
    to access the deployment account
    """
    deployment_account_role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            deployment_account_id,
            config.cross_account_access_role),
        'master'
    )
    for region in list(set([config.deployment_account_region] + config.target_regions)):
        deployment_account_parameter_store = ParameterStore(
            region,
            deployment_account_role
        )
        deployment_account_parameter_store.put_parameter(
            'organization_id', os.environ["ORGANIZATION_ID"]
        )

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
    auto_create_repositories = config.config.get('scm', {}).get('auto-create-repositories')
    if auto_create_repositories is not None:
        deployment_account_parameter_store.put_parameter(
            'auto_create_repositories', str(auto_create_repositories)
        )
    if '@' not in config.notification_endpoint:
        config.notification_channel = config.notification_endpoint
        config.notification_endpoint = "arn:aws:lambda:{0}:{1}:function:SendSlackNotification".format(
            config.deployment_account_region,
            deployment_account_id
        )
    for item in (
            'cross_account_access_role',
            'notification_type',
            'notification_endpoint',
            'notification_channel'
    ):
        if getattr(config, item) is not None:
            deployment_account_parameter_store.put_parameter(
                '/notification_endpoint/main' if item == 'notification_channel' else item,
                str(getattr(config, item))
            )

    return deployment_account_role

def worker_thread(
        account_id,
        sts,
        config,
        s3,
        cache,
        kms_dict):
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

    account_state = is_account_in_invalid_state(ou_id, config.config)
    if account_state:
        LOGGER.info("%s %s", account_id, account_state)
        return

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
        for region in list(set([config.deployment_account_region] + config.target_regions)):
            # Ensuring the kms_arn on the target account is up-to-date
            parameter_store = ParameterStore(region, role)
            parameter_store.put_parameter('kms_arn', kms_dict[region])

            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path=account_path,
                account_id=account_id
            )
            try:
                cloudformation.create_stack()
            except GenericAccountConfigureError as error:
                if 'Unable to fetch parameters' in str(error):
                    LOGGER.error(
                        '%s - Failed to update its base stack due to missing parameters (deployment_account_id or kms_arn), '
                        'ensure this account has been bootstrapped correctly by being moved from the root '
                        'into an Organizational Unit within AWS Organizations.', account_id
                    )
                raise Exception from error

    except GenericAccountConfigureError as generic_account_error:
        LOGGER.info(generic_account_error)
        return

def main(): #pylint: disable=R0915
    LOGGER.info("ADF Version %s", ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    scp = SCP()
    config = Config()
    config.store_config()

    try:
        parameter_store = ParameterStore(REGION_DEFAULT, boto3)
        deployment_account_id = parameter_store.fetch_parameter(
            'deployment_account_id'
        )
        organizations = Organizations(
            role=boto3,
            account_id=deployment_account_id
        )
        scp.apply(organizations, parameter_store, config.config)

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

        # Updating the stack on the master account in deployment region
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
        kms_dict = {}
        # First Setup/Update the Deployment Account in all regions (KMS Key and S3 Bucket + Parameter Store values)
        for region in list(set([config.deployment_account_region] + config.target_regions)):
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=deployment_account_role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path=account_path,
                account_id=deployment_account_id
            )
            cloudformation.create_stack()

            update_deployment_account_output_parameters(
                deployment_account_region=config.deployment_account_region,
                region=region,
                kms_dict=kms_dict,
                deployment_account_role=deployment_account_role,
                cloudformation=cloudformation
            )

        threads = []
        account_ids = organizations.get_account_ids()
        for account_id in [account for account in account_ids if account != deployment_account_id]:
            thread = PropagatingThread(target=worker_thread, args=(
                account_id,
                sts,
                config,
                s3,
                cache,
                kms_dict
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
            'You are now ready to bootstrap a deployment account '
            'by moving it into your deployment OU. '
            'Once you have moved it into the deployment OU, '
            'be sure to check out its progress in AWS Step Functions'
        )
        return


if __name__ == '__main__':
    main()
