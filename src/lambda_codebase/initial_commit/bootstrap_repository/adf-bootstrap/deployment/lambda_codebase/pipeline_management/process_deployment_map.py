"""
Pipeline Management Lambda Function
Triggered by new Deployment Maps in S3 Bucket.
Triggers the pipeline management state machine using the deployment map
as input.
"""


import os
import json
import tempfile
from typing import Any, TypedDict
import hashlib
import yaml
from yaml.error import YAMLError

import boto3
from botocore.exceptions import ClientError
from logger import configure_logger


LOGGER = configure_logger(__name__)
PIPELINE_MANAGEMENT_STATEMACHINE = os.getenv(
    "PIPELINE_MANAGEMENT_STATE_MACHINE",
)
ADF_VERSION = os.getenv("ADF_VERSION")
ADF_VERSION_METADATA_KEY = "adf_version"


class DeploymentMapFileData(TypedDict):
    """
    Class used to return the deployment map file data and its related
    metadata like the execution_id of the CodePipeline that uploaded it.
    """
    content: Any
    execution_id: str


class S3ObjectEvent(TypedDict):
    """
    Class used to return the bucket name and object key
    when a new event is processed.
    """
    bucket_name: str
    object_key: str


def get_details_from_event(event: dict) -> S3ObjectEvent:
    """
    Extract the bucket name and object key from the event dict.

    Args:
        event (dict): The event dictionary that needs to be processed.

    Returns:
        S3ObjectEvent: The bucket name and object key stored inside the event.
    """
    s3_details = event.get("Records", [{}])[0].get("s3")
    if not s3_details:
        raise ValueError("No S3 Event details present in event trigger")
    bucket_name = s3_details.get("bucket", {}).get("name")
    object_key = s3_details.get("object", {}).get("key")
    return {
        "bucket_name": bucket_name,
        "object_key": object_key,
    }


def get_file_from_s3(
    s3_details: S3ObjectEvent,
    s3_resource: boto3.resource,
) -> DeploymentMapFileData:
    """
    Get the file content from the S3 object that was created/updated
    and extract the content and its metadata in a DeploymentMapFileData.

    Args:
        s3_details (S3ObjectEvent): The bucket name and object key of the S3
            object referenced by the event.
        s3_resource (boto3.resource): The S3 resource to use.

    Returns:
        DeploymentMapFileData: The deployment map file content and metadata.
    """
    try:
        s3_object = s3_resource.Object(
            s3_details.get("bucket_name"), s3_details.get("object_key")
        )
        object_adf_version = s3_object.metadata.get(
            ADF_VERSION_METADATA_KEY,
            "n/a",
        )
        if object_adf_version != ADF_VERSION:
            LOGGER.info(
                "Skipping S3 object: %s as it is generated with "
                "an older ADF version ('adf_version' metadata = '%s')",
                s3_details,
                object_adf_version,
            )
            return {
                "content": {},
                "execution_id": ""
            }

        with tempfile.TemporaryFile() as file_pointer:
            s3_object.download_fileobj(file_pointer)

            # Move pointer to the start of the file
            file_pointer.seek(0)

            return {
                "content": yaml.safe_load(file_pointer),
                "execution_id": s3_object.metadata.get("execution_id"),
            }
    except ClientError as error:
        LOGGER.error(
            "Failed to download %s from %s, due to %s",
            s3_details.get('object_key'),
            s3_details.get('bucket_name'),
            error,
        )
        raise
    except YAMLError as yaml_error:
        LOGGER.error(
            "Failed to parse YAML file: %s from %s, due to %s",
            s3_details.get('object_key'),
            s3_details.get('bucket_name'),
            yaml_error,
        )
        raise


def start_executions(
    sfn_client,
    deployment_map_name: str,
    deployment_map,
    codepipeline_execution_id: str,
    request_id: str,
):
    """
    Kick-off the ADF Pipeline Management State Machine.
    Where each pipeline will be created/updated in its own Step Function
    invocation/execution.

    Args:
        sfn_client (boto3.client.StepFunction):
            The Step Function boto3 client.

        deployment_map_name (str):
            The name of the deployment map file that is the initiating source
            of this create/update pipelines process.

        deployment_map (dict):
            The deployment map definition of the pipeline.

        codepipeline_execution_id (str):
            The CodePipeline execution id.

        request_id (str):
            The Lambda function request id.
    """
    if not codepipeline_execution_id:
        codepipeline_execution_id = "no-codepipeline-exec-id-found"
    short_request_id = request_id[-12:]
    run_id = f"{codepipeline_execution_id}-{short_request_id}"
    LOGGER.info(
        "Invoking Pipeline Management State Machine (%s) -> %s",
        PIPELINE_MANAGEMENT_STATEMACHINE,
        run_id
    )
    for pipeline in deployment_map.get("pipelines"):
        LOGGER.debug("Payload: %s", pipeline)
        full_pipeline_name = pipeline.get('name', 'no-pipeline-name')
        # AWS Step Functions supports max 80 characters.
        # Since the run_id equals 49 characters plus the dash, we have 30
        # characters available. To ensure we don't run over in case of 80+
        # characters, lets use a truncated version concatenated with an
        # hash generated from the pipeline name. If below 80 characters, the
        # full_pipeline_name + run_id is used.
        sfn_execution_name = f"{full_pipeline_name}-{run_id}"
        if len(sfn_execution_name) > 80:
            truncated_pipeline_name = full_pipeline_name[:60]
            name_bytes_to_hash = bytes(full_pipeline_name, 'utf-8')
            execution_unique_hash = hashlib.md5(name_bytes_to_hash).hexdigest()[:5]
            sfn_execution_name = f"{truncated_pipeline_name}-{execution_unique_hash}-{run_id}"[:80]
        sfn_client.start_execution(
            stateMachineArn=PIPELINE_MANAGEMENT_STATEMACHINE,
            name=sfn_execution_name,
            input=json.dumps({
                'deployment_map_source': 'S3',
                'deployment_map_name': deployment_map_name,
                'pipeline_definition': pipeline,
            }),
        )


def lambda_handler(event, context):
    """
    Main Lambda Entry point, responsible for iterating over the deployment
    map holding one or more pipelines and initiating the ADF Pipeline
    Management State Machine to create/update the pipelines defined inside.

    Args:
        event (dict): The S3 input event that invoked this Lambda Function.
        context (Context): The Lambda context.

    Returns:
        dict: The input event is returned.
    """
    output = event.copy()
    s3_resource = boto3.resource("s3")
    sfn_client = boto3.client("stepfunctions")
    s3_details = get_details_from_event(event)
    deployment_map = get_file_from_s3(s3_details, s3_resource)
    if deployment_map.get("content"):
        deployment_map["content"]["definition_bucket"] = s3_details.get(
            "object_key",
        )
        start_executions(
            sfn_client,
            s3_details.get("object_key"),
            deployment_map["content"],
            codepipeline_execution_id=deployment_map.get("execution_id"),
            request_id=context.aws_request_id,
        )
    return output
