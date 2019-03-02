# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the pipeline cloudformation stacks
"""

import os
import boto3

from pipeline import Pipeline
from target import Target, TargetStructure
from logger import configure_logger
from deployment_map import DeploymentMap
from cloudformation import CloudFormation
from organizations import Organizations
from sts import STS
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
MASTER_ACCOUNT_ID = os.environ.get("MASTER_ACCOUNT_ID", 'us-east-1')
ADF_PIPELINE_PREFIX = 'adf-pipeline'


def clean(parameter_store, deployment_map):
    """
    Function used to remove stale entries in Parameter Store and
    Deployment Pipelines that are no longer in the Deployment Map
    """
    current_pipeline_parameters = parameter_store.fetch_parameters_by_path(
        '/deployment/')
    for parameter in current_pipeline_parameters:
        name = parameter.get('Name').split('/')[-2]
        if name not in [p.get('name')
                        for p in deployment_map.map_contents['pipelines']]:
            deployment_map.clean_stale_resources(name)


def store_regional_parameter_config(pipeline, parameter_store):
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


def main():
    parameter_store = ParameterStore(
        DEPLOYMENT_ACCOUNT_REGION,
        boto3
    )
    deployment_map = DeploymentMap(
        parameter_store,
        ADF_PIPELINE_PREFIX
    )

    sts = STS(
        boto3
    )
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}-org-access'.format(
            MASTER_ACCOUNT_ID,
            parameter_store.fetch_parameter('cross_account_access_role')
        ), 'pipeline'
    )

    organizations = Organizations(role)
    clean(parameter_store, deployment_map)

    for p in deployment_map.map_contents.get('pipelines'):
        pipeline = Pipeline(p)

        for target in p['targets']:
            target_structure = TargetStructure(target)
            for step in target_structure.target:
                for path in step.get('path'):
                    try:
                        regions = step.get(
                            'regions', p.get(
                                'regions', DEPLOYMENT_ACCOUNT_REGION))
                        pipeline.stage_regions.append(regions)
                        pipeline_target = Target(
                            path, regions, target_structure, organizations)
                        pipeline_target.fetch_accounts_for_target()
                    except BaseException:
                        raise Exception(
                            "Failed to return accounts for {0}".format(path))

            pipeline.template_dictionary["targets"].append(
                target_structure.account_list)

        if DEPLOYMENT_ACCOUNT_REGION not in regions:
            pipeline.stage_regions.append(DEPLOYMENT_ACCOUNT_REGION)

        parameters = pipeline.generate_parameters()
        pipeline.generate()
        deployment_map.update_deployment_parameters(pipeline)

        cloudformation = CloudFormation(
            region=DEPLOYMENT_ACCOUNT_REGION,
            deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
            role=boto3,
            wait=True,
            stack_name="{0}-{1}".format(
                ADF_PIPELINE_PREFIX,
                pipeline.name
            ),
            s3=None,
            s3_key_path=None,
            file_path=pipeline.__dict__.get('file_path'),
            parameters=parameters
        )

        cloudformation.create_stack()
        store_regional_parameter_config(pipeline, parameter_store)


if __name__ == '__main__':
    main()
