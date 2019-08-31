# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the pipeline cloudformation stacks
"""

import random
import os
import time
from thread import PropagatingThread
import boto3

from s3 import S3
from pipeline import Pipeline
from repo import Repo
from target import Target, TargetStructure
from logger import configure_logger
from errors import ParameterNotFoundError
from deployment_map import DeploymentMap
from cloudformation import CloudFormation
from organizations import Organizations
from sts import STS
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
MASTER_ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
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
            parameter_store.delete_parameter(parameter.get('Name'))
            stacks_to_remove.append(name)

    for stack in list(set(stacks_to_remove)):
        cloudformation.delete_stack("{0}-{1}".format(
            ADF_PIPELINE_PREFIX,
            stack
        ))


def store_regional_parameter_config(pipeline, parameter_store):
    """
    Responsible for storing the region information for specific
    pipelines. These regions are defined in the deployment_map
    either as top level regions for a pipeline or stage specific regions
    """
    if pipeline.top_level_regions:
        parameter_store.put_parameter(
            "/deployment/{0}/regions".format(
                pipeline.name
            ),
            str(list(set(pipeline.top_level_regions)))
        )
        return

    parameter_store.put_parameter(
        "/deployment/{0}/regions".format(
            pipeline.name
        ),
        str(list(set(Pipeline.flatten_list(pipeline.stage_regions))))
    )

def upload_pipeline(s3, pipeline):
    """
    Responsible for uploading the object (global.yml) to S3
    and returning the URL that can be referenced in the CloudFormation
    create_stack call.
    """
    s3_object_path = s3.put_object(
        "pipelines/{0}/global.yml".format(
            pipeline.name), "{0}/{1}/global.yml".format(
                'pipelines',
                pipeline.name
            )
        )
    return s3_object_path

def worker_thread(p, organizations, auto_create_repositories, s3, deployment_map, parameter_store):
    pipeline = Pipeline(p)

    if auto_create_repositories == 'enabled':
        try:
            code_account_id = next(param['SourceAccountId'] for param in p['params'] if 'SourceAccountId' in param)
            has_custom_repo = bool([item for item in p['params'] if 'RepositoryName' in item])
            if auto_create_repositories and code_account_id and str(code_account_id).isdigit() and not has_custom_repo:
                repo = Repo(code_account_id, p.get('name'), p.get('description'))
                repo.create_update()
        except StopIteration:
            LOGGER.debug("No need to create repository as SourceAccountId is not found in params")

    for target in p.get('targets', []):
        target_structure = TargetStructure(target)
        for step in target_structure.target:
            for path in step.get('path'):
                regions = step.get(
                    'regions', p.get(
                        'regions', DEPLOYMENT_ACCOUNT_REGION))
                step_name = step.get('name')
                params = step.get('params', {})
                pipeline.stage_regions.append(regions)
                pipeline_target = Target(
                    path, regions, target_structure, organizations, step_name, params)
                pipeline_target.fetch_accounts_for_target()

        pipeline.template_dictionary["targets"].append(
            target_structure.account_list)

        if DEPLOYMENT_ACCOUNT_REGION not in regions:
            pipeline.stage_regions.append(DEPLOYMENT_ACCOUNT_REGION)

    parameters = pipeline.generate_parameters()
    pipeline.generate()
    deployment_map.update_deployment_parameters(pipeline)
    s3_object_path = upload_pipeline(s3, pipeline)

    store_regional_parameter_config(pipeline, parameter_store)
    cloudformation = CloudFormation(
        region=DEPLOYMENT_ACCOUNT_REGION,
        deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
        role=boto3,
        template_url=s3_object_path,
        parameters=parameters,
        wait=True,
        stack_name="{0}-{1}".format(
            ADF_PIPELINE_PREFIX,
            pipeline.name
        ),
        s3=None,
        s3_key_path=None,
        account_id=DEPLOYMENT_ACCOUNT_ID
    )
    cloudformation.create_stack()

def main():
    LOGGER.info('ADF Version %s', ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    parameter_store = ParameterStore(
        DEPLOYMENT_ACCOUNT_REGION,
        boto3
    )
    deployment_map = DeploymentMap(
        parameter_store,
        ADF_PIPELINE_PREFIX
    )
    s3 = S3(
        DEPLOYMENT_ACCOUNT_REGION,
        S3_BUCKET_NAME
    )
    sts = STS()
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}-readonly'.format(
            MASTER_ACCOUNT_ID,
            parameter_store.fetch_parameter('cross_account_access_role')
        ), 'pipeline'
    )

    organizations = Organizations(role)
    clean(parameter_store, deployment_map)

    try:
        auto_create_repositories = parameter_store.fetch_parameter('auto_create_repositories')
    except ParameterNotFoundError:
        auto_create_repositories = 'enabled'

    threads = []
    for counter, p in enumerate(deployment_map.map_contents.get('pipelines')):
        thread = PropagatingThread(target=worker_thread, args=(
            p,
            organizations,
            auto_create_repositories,
            s3,
            deployment_map,
            parameter_store
        ))
        thread.start()
        threads.append(thread)
        _batcher = counter % 10
        if _batcher == 9: # 9 meaning we have hit a set of 10 threads since n % 10
            _interval = random.randint(5, 11)
            LOGGER.debug('Waiting for %s seconds before starting next batch of 10 threads.', _interval)
            time.sleep(_interval)

    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
