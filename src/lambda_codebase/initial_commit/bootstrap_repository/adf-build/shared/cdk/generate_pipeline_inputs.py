#!/usr/bin/env python3

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the pipeline cloudformation stack inputs
"""
import json
import os
from thread import PropagatingThread

import boto3
from cache import Cache
from deployment_map import DeploymentMap
from errors import ParameterNotFoundError
from logger import configure_logger
from organizations import Organizations
from parameter_store import ParameterStore
from partition import get_partition
from pipeline import Pipeline
from repo import Repo
from rule import Rule
from s3 import S3
from sts import STS
from target import Target, TargetStructure

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
MASTER_ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
ORGANIZATION_ID = os.environ["ORGANIZATION_ID"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
SHARED_MODULES_BUCKET = os.environ["SHARED_MODULES_BUCKET"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]


def ensure_event_bus_status(organization_id):
    _events = boto3.client('events')
    _events.put_permission(
        Action='events:PutEvents',
        Principal='*',
        StatementId='OrgAccessForEventBus',
        Condition={
            'Type': 'StringEquals',
            'Key': 'aws:PrincipalOrgID',
            'Value': organization_id
        }
    )


def store_regional_parameter_config(pipeline, parameter_store):
    """
    Responsible for storing the region information for specific
    pipelines. These regions are defined in the deployment_map
    either as top level regions for a pipeline or stage specific regions
    """
    if pipeline.top_level_regions:
        parameter_store.put_parameter(
            f"/deployment/{pipeline.nam}/regions",
            str(list(set(pipeline.top_level_regions)))
        )
        return

    parameter_store.put_parameter(
        f"/deployment/{pipeline.name}/regions",
        str(list(set(Pipeline.flatten_list(pipeline.stage_regions))))
    )


def fetch_required_ssm_params(regions):
    output = {}
    for region in regions:
        parameter_store = ParameterStore(region, boto3)
        output[region] = {
            "s3": parameter_store.fetch_parameter(
                f'/cross_region/s3_regional_bucket/{region}',
            ),
            "kms": parameter_store.fetch_parameter(
                f'/cross_region/kms_arn/{region}',
            ),
        }
        if region == DEPLOYMENT_ACCOUNT_REGION:
            output[region]["modules"] = parameter_store.fetch_parameter('deployment_account_bucket')
            output['default_scm_branch'] = parameter_store.fetch_parameter('default_scm_branch')
    return output


def worker_thread(p, organizations, auto_create_repositories, deployment_map, parameter_store):
    LOGGER.debug("Worker Thread started for %s", p.get('name'))
    pipeline = Pipeline(p)
    if auto_create_repositories == 'enabled':
        code_account_id = p.get('default_providers', {}).get('source', {}).get('properties', {}).get('account_id', {})
        has_custom_repo = p.get('default_providers', {}).get('source', {}).get('properties', {}).get('repository', {})
        if auto_create_repositories and code_account_id and str(code_account_id).isdigit() and not has_custom_repo:
            repo = Repo(code_account_id, p.get('name'), p.get('description'))
            repo.create_update()

    regions = []
    for target in p.get('targets', []):
        target_structure = TargetStructure(target)
        for step in target_structure.target:
            regions = step.get(
                'regions', p.get(
                    'regions', DEPLOYMENT_ACCOUNT_REGION))
            paths_tags = []
            for path in step.get('path', []):
                paths_tags.append(path)
            if step.get('tags') is not None:
                paths_tags.append(step.get('tags', {}))
            for path_or_tag in paths_tags:
                pipeline.stage_regions.append(regions)
                pipeline_target = Target(path_or_tag, target_structure, organizations, step, regions)
                pipeline_target.fetch_accounts_for_target()

            pipeline.template_dictionary["targets"].append(target.target_structure.generate_waves())

    if DEPLOYMENT_ACCOUNT_REGION not in regions:
        pipeline.stage_regions.append(DEPLOYMENT_ACCOUNT_REGION)
    pipeline.generate_input()
    ssm_params = fetch_required_ssm_params(
        pipeline.input["regions"] or [DEPLOYMENT_ACCOUNT_REGION]
    )
    deployment_map.update_deployment_parameters(pipeline)
    store_regional_parameter_config(pipeline, parameter_store)
    with open(f'cdk_inputs/{pipeline.input["name"]}.json', mode='w', encoding='utf-8') as outfile:
        data = {}
        data['input'] = pipeline.input
        data['input']['default_scm_branch'] = ssm_params.get('default_scm_branch')
        data['ssm_params'] = ssm_params
        json.dump(data, outfile)


def _create_inputs_folder():
    try:
        return os.mkdir('cdk_inputs')
    except FileExistsError:
        return None


def main():
    LOGGER.info('ADF Version %s', ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    _create_inputs_folder()
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
    sts = STS()
    partition = get_partition(DEPLOYMENT_ACCOUNT_REGION)
    cross_account_access_role = parameter_store.fetch_parameter('cross_account_access_role')
    role = sts.assume_cross_account_role(
        f'arn:{partition}:iam::{MASTER_ACCOUNT_ID}:role/'
        f'{cross_account_access_role}-readonly',
        'pipeline'
    )
    organizations = Organizations(role)
    ensure_event_bus_status(ORGANIZATION_ID)
    try:
        auto_create_repositories = parameter_store.fetch_parameter('auto_create_repositories')
    except ParameterNotFoundError:
        auto_create_repositories = 'enabled'
    threads = []
    _cache = Cache()
    for p in deployment_map.map_contents.get('pipelines', []):
        _source_account_id = p.get('default_providers', {}).get('source', {}).get('properties', {}).get('account_id', {})
        if _source_account_id and int(_source_account_id) != int(DEPLOYMENT_ACCOUNT_ID) and not _cache.check(_source_account_id):
            rule = Rule(p['default_providers']['source']['properties']['account_id'])
            rule.create_update()
            _cache.add(p['default_providers']['source']['properties']['account_id'], True)
        thread = PropagatingThread(target=worker_thread, args=(
            p,
            organizations,
            auto_create_repositories,
            deployment_map,
            parameter_store
        ))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
