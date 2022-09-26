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


LOGGER = configure_logger(__name__)
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_PREFIX = "/deployment/"
S3_BACKED_DEPLOYMENT_PREFIX = f"{DEPLOYMENT_PREFIX}S3/"


def download_deployment_maps(resource, prefix, local):
    paginator = resource.meta.client.get_paginator("list_objects")
    for result in paginator.paginate(
        Bucket=S3_BUCKET_NAME, Delimiter="/", Prefix=prefix
    ):
        LOGGER.debug("Downloaded deployment map: %s", result)
        for subdir in result.get("CommonPrefixes", []):
            download_deployment_maps(resource, subdir.get("Prefix"), local)
        for file in result.get("Contents", []):
            LOGGER.debug("File content in deployment map: %s", file)
            dest_path_name = os.path.join(local, file.get("Key"))
            if not os.path.exists(os.path.dirname(dest_path_name)):
                os.makedirs(os.path.dirname(dest_path_name))
            resource.meta.client.download_file(
                S3_BUCKET_NAME, file.get("Key"), dest_path_name
            )


def get_current_pipelines(parameter_store):
    return parameter_store.fetch_parameters_by_path(S3_BACKED_DEPLOYMENT_PREFIX)


def identify_out_of_date_pipelines(pipeline_names, current_pipelines):
    return [
        {
            "full_pipeline_name": f"{ADF_PIPELINE_PREFIX}{name}",
            "pipeline_name": name,
        }
        for name in current_pipelines.difference(pipeline_names)
    ]


def lambda_handler(event, _):
    output = event.copy()
    s3 = boto3.resource("s3")
    deployment_map = None
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        download_deployment_maps(s3, "", tmp_dir_path)
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
        pipeline_names, current_pipelines
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
