# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the pipeline cloudformation stacks
"""

import os
import boto3

from s3 import S3
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
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

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
            pipeline.name), "{0}/{1}/{2}/global.yml".format(
                TARGET_DIR,
                'pipelines',
                pipeline.name
            )
        )
    return s3_object_path


def main(): #pylint: disable=R0915
    parameter_store = ParameterStore(
        DEPLOYMENT_ACCOUNT_REGION,
        boto3
    )
    deployment_map = DeploymentMap(
        parameter_store,
        os.environ["ADF_PIPELINE_PREFIX"]
    )
    s3 = S3(
        DEPLOYMENT_ACCOUNT_REGION,
        S3_BUCKET_NAME
    )
    sts = STS()
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            MASTER_ACCOUNT_ID,
            parameter_store.fetch_parameter('cross_account_access_role')
        ), 'pipeline'
    )

    organizations = Organizations(role)
    clean(parameter_store, deployment_map)

    for p in deployment_map.map_contents.get('pipelines'):
        pipeline = Pipeline(p)

        for target in p.get('targets', []):
            target_structure = TargetStructure(target)
            for step in target_structure.target:
                for path in step.get('path'):
                    regions = step.get(
                        'regions', p.get(
                            'regions', DEPLOYMENT_ACCOUNT_REGION))
                    step_name = step.get('name')
                    pipeline.stage_regions.append(regions)
                    pipeline_target = Target(
                        path, regions, target_structure, organizations, step_name)
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
                os.environ["ADF_PIPELINE_PREFIX"],
                pipeline.name
            ),
            s3=None,
            s3_key_path=None
        )
        cloudformation.validate_template()
        cloudformation.create_stack()


if __name__ == '__main__':
    main()
