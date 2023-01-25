"""
Pipeline Management Lambda Function
Compares pipeline definitions in S3 to the definitions stored in SSM Param Store.
Any that exist in param store but not S3 are marked for removal.
Uses the /deployment/S3/ prefix to make a decision on if a pipeline is stored in S3 or not
"""

import os
import json
import hashlib
import tempfile

import boto3

from logger import configure_logger
from deployment_map import DeploymentMap
from parameter_store import ParameterStore
from aws_xray_sdk.core import patch_all


patch_all()
LOGGER = configure_logger(__name__)
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_PREFIX = "/deployment/"
S3_BACKED_DEPLOYMENT_PREFIX = f"{DEPLOYMENT_PREFIX}S3/"


def download_deployment_maps(s3_resource, prefix, local):
    """
    Download the deployment maps using the S3 resource.
    It will only iterate over the deployment maps that match the specified
    prefix and will store them in the local directory as requested.

    If any CommonPrefixes are found (like folders in a file system), then
    it will call itself recursively.

    Args:
        s3_resource (boto3.resource.S3): The S3 resource to use.

        prefix (str): The prefix that the objects should match.

        local (str): The local directory to store the files.
    """
    paginator = s3_resource.meta.client.get_paginator("list_objects")
    for result in paginator.paginate(
        Bucket=S3_BUCKET_NAME, Delimiter="/", Prefix=prefix
    ):
        LOGGER.debug("Found the following deployment map: %s", result)
        for subdir in result.get("CommonPrefixes", []):
            # Recursive call:
            download_deployment_maps(
                s3_resource,
                subdir.get("Prefix"),
                local,
            )

        for file in result.get("Contents", []):
            LOGGER.debug("File content in deployment map: %s", file)
            dest_path_name = os.path.join(local, file.get("Key"))
            if not os.path.exists(os.path.dirname(dest_path_name)):
                os.makedirs(os.path.dirname(dest_path_name))
            s3_resource.meta.client.download_file(
                S3_BUCKET_NAME,
                file.get("Key"),
                dest_path_name,
            )


def get_current_pipelines(parameter_store):
    """
    Get pipelines that are defined currently.

    Args:
        parameter_store (ParameterStore): The ParameterStore class instance
            to use.

    Returns:
        [str]: The parameter keys of the pipelines defined, these could include
            stale pipelines.
    """
    return parameter_store.fetch_parameters_by_path(
        S3_BACKED_DEPLOYMENT_PREFIX,
    )


def identify_out_of_date_pipelines(pipeline_names, current_pipelines):
    """
    Identify which pipelines are out of date.

    Args:
        pipeline_names (set[str]): The pipeline names that should remain.

        current_pipelines (set[str]): The pipelines defined at the moment,
            including the pipeline names that could be stale.
    """
    return [
        {
            "full_pipeline_name": f"{ADF_PIPELINE_PREFIX}{name}",
            "pipeline_name": name,
        }
        for name in current_pipelines.difference(pipeline_names)
    ]


def lambda_handler(event, _):
    """
    Lambda handler, processing the pipelines that are defined and matching
    those against the parameters of the pipelines that were created before.

    The pipelines that have parameters but are no longer defined are stale
    and should be deleted.

    Args:
        event (dict): The input event from the ADF Pipeline Management state
            machine.

    Returns:
        dict: The pipelines to be deleted, the traceroot, and hash of the
            pipeline to be deleted dict.
    """
    LOGGER.debug("Received: %s", event)
    s3_resource = boto3.resource("s3")
    deployment_map = None
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        download_deployment_maps(s3_resource, "", tmp_dir_path)
        deployment_map = DeploymentMap(
            None,
            None,
            None,
            map_path=f"{tmp_dir_path}/deployment_map.yml",
            map_dir_path=tmp_dir_path,
        )
    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    current_pipelines = {
        parameter.get("Name").split("/")[-2]
        for parameter in get_current_pipelines(parameter_store)
    }

    pipeline_names = {
        p.get("name") for p in deployment_map.map_contents["pipelines"]
    }
    out_of_date_pipelines = identify_out_of_date_pipelines(
        pipeline_names,
        current_pipelines,
    )

    output = {}
    if len(out_of_date_pipelines) > 0:
        output["pipelines_to_be_deleted"] = out_of_date_pipelines

    data_md5 = hashlib.md5(
        json.dumps(output, sort_keys=True).encode("utf-8")
    ).hexdigest()
    root_trace_id = os.getenv("_X_AMZN_TRACE_ID", "na=na;na=na").split(";")[0]
    output["traceroot"] = root_trace_id
    output["hash"] = data_md5
    return output
