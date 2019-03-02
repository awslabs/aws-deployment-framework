# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Main entry point for main.py execution which
is executed from within AWS CodeBuild in the Master Account
"""

import os
from thread import PropagatingThread

import boto3
from logger import configure_logger
from cache import Cache
from cloudformation import CloudFormation
from parameter_store import ParameterStore
from organizations import Organizations
from stepfunctions import StepFunctions
from errors import NotConfiguredError, GenericAccountConfigureError
from sts import STS
from s3 import S3
from config import Config


S3_BUCKET = os.environ["S3_BUCKET"]
REGION_DEFAULT = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_S3_BUCKET = os.environ["DEPLOYMENT_ACCOUNT_BUCKET"]
LOGGER = configure_logger(__name__)


def is_account_invalid_state(ou_id, config):
    # Account is sitting in the root of the Organization or in Protected OU
    return ou_id.startswith('r-') or ou_id in config.get('protected', [])


def ensure_deployment_account_configured(
        sts,
        config,
        ou_id,
        deployment_account_id):
    """
    If the Deployment Account is in an valid state return the role to assume
    """
    if is_account_invalid_state(ou_id, config.config):
        raise NotConfiguredError(
            'Deployment Account is not yet setup, '
            'nothing can require an update'
        )
    return prepare_deployment_account(sts, deployment_account_id, config)


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
    except BaseException:
        raise GenericAccountConfigureError(
            'Generic Account cannot yet be setup, '
            'Base stack is not present'
        )


def update_deployment_account_output_parameters(
        deployment_account_region,
        region,
        deployment_account_role,
        cloudformation):
    deployment_account_parameter_store = ParameterStore(
        deployment_account_region, deployment_account_role
    )
    parameter_store = ParameterStore(
        region, deployment_account_role
    )

    for key, value in cloudformation.get_stack_regional_outputs().items():
        deployment_account_parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )
        parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )


def prepare_deployment_account(sts, deployment_account_id, config):
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
        'cross_account_access_role', str(config.cross_account_access_role)
    )
    deployment_account_parameter_store.put_parameter(
        'deployment_account_bucket', DEPLOYMENT_ACCOUNT_S3_BUCKET
    )
    return deployment_account_role


def worker_thread(
        account_id,
        sts,
        config,
        s3,
        cache):
    LOGGER.info("Starting new worker thread for %s", account_id)

    organizations = Organizations(
        boto3,
        account_id
    )
    ou_id = organizations.get_parent_info().get("ou_parent_id")
    if is_account_invalid_state(ou_id, config.config):
        LOGGER.info("%s is in an invalid state", account_id)
        return

    account_path = organizations.build_account_path(
        ou_id,
        [],  # Initial empty array to hold OU Path,
        cache
    )
    LOGGER.info("The Account path is %s", account_path)

    try:
        role = ensure_generic_account_can_be_setup(
            sts,
            config,
            account_id
        )

        # Regional base stacks can be updated after global
        for region in list(set([config.deployment_account_region] + config.target_regions)):
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path=account_path,
                file_path=None,
            )

            cloudformation.create_stack()

    except GenericAccountConfigureError as generic_account_error:
        LOGGER.info(generic_account_error)
        return


def main():
    try:
        parameter_store = ParameterStore(REGION_DEFAULT, boto3)
        deployment_account_id = parameter_store.fetch_parameter(
            'deployment_account_id'
        )

        config = Config()
        config.store_config()

        if deployment_account_id is None:
            raise NotConfiguredError(
                "Deployment Account has not yet been configured"
            )

        organizations = Organizations(
            boto3,
            deployment_account_id
        )

        sts = STS(boto3)
        ou_id = organizations.get_parent_info().get("ou_parent_id")

        deployment_account_role = ensure_deployment_account_configured(
            sts,
            config,
            ou_id,
            deployment_account_id
        )

        cache = Cache()
        account_path = organizations.build_account_path(
            ou_id,
            [],  # Initial empty array to hold OU Path
            cache
        )

        s3 = S3(
            REGION_DEFAULT,
            boto3,
            S3_BUCKET
        )

        # (First) Setup the Deployment Account in all regions (KMS Key and S3 Bucket + Parameter Store values)
        for region in list(set([config.deployment_account_region] + config.target_regions)):
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=config.deployment_account_region,
                role=deployment_account_role,
                wait=True,
                stack_name=None,
                s3=s3,
                s3_key_path=account_path,
                file_path=None,
            )

            cloudformation.create_stack()

            update_deployment_account_output_parameters(
                deployment_account_region=config.deployment_account_region,
                region=region,
                deployment_account_role=deployment_account_role,
                cloudformation=cloudformation
            )

        threads = []
        account_ids = organizations.get_account_ids()
        for account_id in account_ids:
            t = PropagatingThread(target=worker_thread, args=(
                account_id,
                sts,
                config,
                s3,
                cache
            ))
            t.start()
            threads.append(t)

        for thread in threads:
            thread.join()

        step_functions = StepFunctions(
            role=deployment_account_role,
            deployment_account_id=deployment_account_id,
            deployment_account_region=config.deployment_account_region,
            regions=config.target_regions,
            account_ids=[i for i in account_ids if i != config.deployment_account_region],
            update_pipelines_only=False
        )

        step_functions.execute_statemachine()

    except NotConfiguredError as not_configured_error:
        LOGGER.info(not_configured_error)


if __name__ == '__main__':
    main()
