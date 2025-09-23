# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

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
MANAGEMENT_ACCOUNT_ID = os.environ["MANAGEMENT_ACCOUNT_ID"]

ORGANIZATIONS_READONLY_ROLE = "adf/organizations/adf-organizations-readonly"


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
    parameter_store.put_parameter(
        f"deployment/{deployment_map_source}/{pipeline.name}/regions",
        str(pipeline.get_all_regions()),
    )


def fetch_required_ssm_params(pipeline_input, regions):
    """
    Fetch the required SSM parameters for the regions of this pipeline.

    Args:
        pipeline_input (dict): The pipeline input dictionary.

        regions ([str]): The regions of the pipeline.

    Returns:
        dict[str, dict[str,str] | str]:
            The SSM parameters in a dictionary. Where the key is the region or
            a generic SSM parameter key for this pipeline. The value is either
            a dictionary holding the key/value pairs of SSM parameters, or the
            value of the generic SSM parameter.
    """
    output = {}
    for region in regions:
        parameter_store = ParameterStore(region, boto3)
        output[region] = {
            "s3": parameter_store.fetch_parameter(
                f"cross_region/s3_regional_bucket/{region}",
            ),
            "kms": parameter_store.fetch_parameter(
                f"cross_region/kms_arn/{region}",
            ),
        }
        if region == DEPLOYMENT_ACCOUNT_REGION:
            output[region]["modules"] = parameter_store.fetch_parameter(
                "shared_modules_bucket"
            )
            output["default_scm_branch"] = parameter_store.fetch_parameter(
                "scm/default_scm_branch",
            )
            output["default_scm_codecommit_account_id"] = parameter_store.fetch_parameter(
                "scm/default_scm_codecommit_account_id",
            )
            codeconnections_param_path = (
                pipeline_input
                .get("default_providers", {})
                .get("source")
                .get("properties", {})
                .get("codeconnections_param_path")
            )
            if codeconnections_param_path:
                output["codeconnections_arn"] = (
                    parameter_store.fetch_parameter(codeconnections_param_path)
                )
    return output


def report_final_pipeline_targets(pipeline_object):
    number_of_targets = 0
    LOGGER.info(
        "Targets found: %s",
        pipeline_object.template_dictionary["targets"],
    )
    for target in pipeline_object.template_dictionary["targets"]:
        for target_accounts in target:
            number_of_targets = number_of_targets + len(target_accounts)
    LOGGER.info("Number of targets found: %d", number_of_targets)
    if number_of_targets == 0:
        LOGGER.info("Attempting to create an empty pipeline as there were no targets found")

# pylint: disable=R0914
def generate_pipeline_inputs(
    pipeline,
    deployment_map_source,
    organizations,
    parameter_store,
):
    """
    Generate the pipeline inputs for the given pipeline definition.

    Args:
        pipeline (dict): The pipeline definition, as specified in the
            deployment map that defines this pipeline.

        deployment_map_source (str): The deployment map source (i.e. "S3").

        organizations (Organizations): The Organizations class instance.

        parameter_store (ParameterStore): The Parameter Store class instance.
    """
    data = {}
    pipeline_object = Pipeline(pipeline)
    total_pipeline_actions = 2
    # Assumption is that a Source and Build Stage is = 2 Actions
    for target in pipeline.get("targets", []):
        target_structure = TargetStructure(target)
        for raw_step in target_structure.target:
            step = pipeline_object.merge_in_deploy_defaults(raw_step)
            paths_tags = []
            for path in step.get("path", []):
                paths_tags.append(path)
            if step.get("tags") is not None:
                paths_tags.append(step.get("tags", {}))
            for path_or_tag in paths_tags:
                pipeline_object.stage_regions.append(step.get("regions"))
                pipeline_target = Target(
                    path_or_tag,
                    target_structure,
                    organizations,
                    step,
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

        waves, wave_action_count =  target_structure.generate_waves(
            target=pipeline_target
        )
        pipeline_object.template_dictionary["targets"].append(list(waves))
        # Add the actions from the waves to the total_pipeline_actions count
        total_pipeline_actions += wave_action_count

    target_structure.validate_actions_limit(
        pipeline.get("name"),
        total_pipeline_actions
    )

    report_final_pipeline_targets(pipeline_object)

    if DEPLOYMENT_ACCOUNT_REGION not in pipeline_object.stage_regions:
        pipeline_object.stage_regions.append(DEPLOYMENT_ACCOUNT_REGION)

    data["pipeline_input"] = pipeline_object.generate_input()
    data["ssm_params"] = fetch_required_ssm_params(
        data["pipeline_input"],
        data["pipeline_input"]["regions"],
    )
    if "codeconnections_arn" in data["ssm_params"]:
        data["pipeline_input"]["default_providers"]["source"]["properties"][
            "codeconnections_arn"
        ] = data["ssm_params"]["codeconnections_arn"]
    data["pipeline_input"].update({
        "default_scm_branch": data["ssm_params"].get("default_scm_branch"),
        "default_scm_codecommit_account_id": data["ssm_params"].get(
            "default_scm_codecommit_account_id"
        )
    })
    store_regional_parameter_config(
        pipeline_object,
        parameter_store,
        deployment_map_source,
    )
    return data


def lambda_handler(event, _):
    """
    Main Lambda Entry point, responsible to generate the pipeline input
    data based on the pipeline definition.

    Args:
        event (dict): The ADF Pipeline Management State Machine input object,
            holding the pipeline definition.

    Returns:
        dict: The input event enriched with the pipeline inputs and ssm
            parameter values retrieved.
    """
    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    sts = STS()
    role = sts.assume_cross_account_role(
        (
            f"arn:{get_partition(DEPLOYMENT_ACCOUNT_REGION)}:iam::"
            f"{MANAGEMENT_ACCOUNT_ID}:role/{ORGANIZATIONS_READONLY_ROLE}"
        ),
        "pipeline",
    )
    organizations = Organizations(role)

    pipeline_input_data = generate_pipeline_inputs(
        event.get("pipeline_definition"),
        event.get("deployment_map_source"),
        organizations,
        parameter_store,
    )

    return {
        **event,
        **pipeline_input_data,
    }
