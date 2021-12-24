#!/usr/bin/env python3

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to remove stale SSM Parameter Store entries and delete
   the CloudFormation stacks for pipelines that are no longer defined
   in the deployment map(s)
"""

import os
import boto3

from s3 import S3
from logger import configure_logger
from deployment_map import DeploymentMap
from cloudformation import CloudFormation
from parameter_store import ParameterStore


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
MASTER_ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
ORGANIZATION_ID = os.environ["ORGANIZATION_ID"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
SHARED_MODULES_BUCKET = os.environ["SHARED_MODULES_BUCKET"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]

def clean(parameter_store, deployment_map):
    """
    Function used to remove stale entries in Parameter Store and
    Deployment Pipelines that are no longer in the Deployment Map
    """
    current_pipeline_parameters = parameter_store.fetch_parameters_by_path(
        '/deployment/')

    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    cloudformation = CloudFormation(
        region=DEPLOYMENT_ACCOUNT_REGION,
        deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
        role=boto3
    )
    stacks_to_remove = []
    for parameter in current_pipeline_parameters:
        name = parameter.get('Name').split('/')[-2]
        if name not in [p.get('name') for p in deployment_map.map_contents['pipelines']]:
            LOGGER.info(f'Deleting {parameter.get("Name")}')
            parameter_store.delete_parameter(parameter.get('Name'))
            stacks_to_remove.append(name)

    for stack in list(set(stacks_to_remove)):
        cloudformation.delete_stack(f"{ADF_PIPELINE_PREFIX}{stack}")


def main():
    LOGGER.info('ADF Version %s', ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    parameter_store = ParameterStore(
        DEPLOYMENT_ACCOUNT_REGION,
        boto3
    )

    s3 = S3(DEPLOYMENT_ACCOUNT_REGION, SHARED_MODULES_BUCKET)
    deployment_map = DeploymentMap(
        parameter_store,
        s3,
        ADF_PIPELINE_PREFIX
    )

    LOGGER.info('Cleaning Stale Deployment Map entries')
    clean(parameter_store, deployment_map)


if __name__ == '__main__':
    main()
