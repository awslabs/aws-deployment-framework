"""
Pipeline Management Lambda Function
Generates Pipeline Inputs
"""

import os
import boto3

from pipeline import Pipeline
from target import Target, TargetStructure
from organizations import Organizations
from parameter_store import ParameterStore
from sts import STS
from logger import configure_logger
from partition import get_partition


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ROOT_ACCOUNT_ID = os.environ["ROOT_ACCOUNT_ID"]


def store_regional_parameter_config(
    pipeline,
    parameter_store,
    deployment_map_source,
):
    """
    Responsible for storing the region information for specific
    pipelines. These regions are defined in the deployment_map
    either as top level regions for a pipeline or stage specific regions
    These are only used to track pipelines.
    """
    if pipeline.top_level_regions:
        parameter_store.put_parameter(
            f"/deployment/{deployment_map_source}/{pipeline.name}/regions",
            str(list(set(pipeline.top_level_regions))),
        )
        return

    parameter_store.put_parameter(
        f"/deployment/{deployment_map_source}/{pipeline.name}/regions",
        str(list(set(Pipeline.flatten_list(pipeline.stage_regions)))),
    )


def fetch_required_ssm_params(pipeline_input, regions):
    output = {}
    for region in regions:
        parameter_store = ParameterStore(region, boto3)
        output[region] = {
            "s3": parameter_store.fetch_parameter(
                f"/cross_region/s3_regional_bucket/{region}",
            ),
            "kms": parameter_store.fetch_parameter(
                f"/cross_region/kms_arn/{region}",
            ),
        }
        if region == DEPLOYMENT_ACCOUNT_REGION:
            output[region]["modules"] = parameter_store.fetch_parameter(
                "deployment_account_bucket"
            )
            output['default_scm_branch'] = parameter_store.fetch_parameter(
                'default_scm_branch',
            )
            codestar_connection_path = (
                pipeline_input
                .get('default_providers', {})
                .get('source')
                .get('properties', {})
                .get('codestar_connection_path', {})
            )
            if codestar_connection_path:
                output['codestar_connection_arn'] = (
                    parameter_store.fetch_parameter(codestar_connection_path)
                )
    return output


def generate_pipeline_inputs(pipeline, organizations, parameter_store):
    data = {}
    pipeline_object = Pipeline(pipeline)
    regions = []

    for target in pipeline.get("targets", []):
        target_structure = TargetStructure(target)
        for step in target_structure.target:
            regions = step.get(
                "regions", pipeline.get("regions", DEPLOYMENT_ACCOUNT_REGION)
            )
            paths_tags = []
            for path in step.get("path", []):
                paths_tags.append(path)
            if step.get("tags") is not None:
                paths_tags.append(step.get("tags", {}))
            for path_or_tag in paths_tags:
                pipeline_object.stage_regions.append(regions)
                pipeline_target = Target(
                    path_or_tag, target_structure, organizations, step, regions
                )
                pipeline_target.fetch_accounts_for_target()
        # Targets should be a list of lists.

        # Note: This is a big shift away from how ADF handles targets natively.
        # Previously this would be a list of [accountId(s)] it now returns a
        # list of [[account_ids], [account_ids]].
        #
        # For the sake of consistency we should probably think of a target
        # consisting of multiple "waves". So if you see any reference to
        # a wave going forward it will be the individual batch of account ids.
        pipeline_object.template_dictionary["targets"].append(
            list(target_structure.generate_waves()),
        )

    if DEPLOYMENT_ACCOUNT_REGION not in regions:
        pipeline_object.stage_regions.append(DEPLOYMENT_ACCOUNT_REGION)

    pipeline_object.generate_input()
    data["ssm_params"] = fetch_required_ssm_params(
        pipeline_object.input,
        pipeline_object.input["regions"] or [DEPLOYMENT_ACCOUNT_REGION]
    )
    data["input"] = pipeline_object.input
    if 'codestar_connection_arn' in data["ssm_params"]:
        data['input']['default_providers']['source']['properties'][
            'codestar_connection_arn'
        ] = data["ssm_params"]['codestar_connection_arn']
    data['input']['default_scm_branch'] = data["ssm_params"].get(
        'default_scm_branch',
    )
    store_regional_parameter_config(
        pipeline_object,
        parameter_store,
        pipeline.get("deployment_map_source"),
    )
    return data


def lambda_handler(pipeline, _):
    """Main Lambda Entry point"""
    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    sts = STS()
    cross_account_role_name = parameter_store.fetch_parameter(
        "cross_account_access_role",
    )
    role = sts.assume_cross_account_role(
        (
            f'arn:{get_partition(DEPLOYMENT_ACCOUNT_REGION)}:iam::'
            f'{ROOT_ACCOUNT_ID}:role/{cross_account_role_name}-readonly'
        ),
        "pipeline",
    )
    organizations = Organizations(role)

    output = generate_pipeline_inputs(pipeline, organizations, parameter_store)

    return output
