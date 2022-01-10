"""
Pipeline Management Lambda Function
Triggered by new Deployment Maps in S3 Bucket.
Triggers the pipeline management state machine using the deployment map as input.
"""


import os
import json
import tempfile
import yaml
from yaml.error import YAMLError

import boto3
from botocore.exceptions import ClientError
from logger import configure_logger


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
PIPELINE_MANAGEMENT_STATEMACHINE = os.getenv("PIPELINE_MANAGEMENT_STATE_MACHINE")


_cache = None


def get_details_from_event(event: dict):
    s3_details = event.get("Records", [{}])[0].get("s3")
    if not s3_details:
        raise ValueError("No S3 Event details present in event trigger")
    bucket_name = s3_details.get("bucket", {}).get("name")
    object_key = s3_details.get("object", {}).get("key")
    return {
        "bucket_name": bucket_name,
        "object_key": object_key,
    }


def get_file_from_s3(s3_details: dict, s3_resource: boto3.resource):
    try:
        s3_object = s3_resource.Object(
            s3_details.get("bucket_name"), s3_details.get("object_key")
        )
        with tempfile.TemporaryFile() as file_pointer:
            s3_object.download_fileobj(file_pointer)

            # Move pointer to the start of the file
            file_pointer.seek(0)

            return yaml.safe_load(file_pointer)
    except ClientError as error:
        LOGGER.error(
            f"Failed to download {s3_details.get('object_key')} "
            f"from {s3_details.get('bucket_name')}, due to {error}"
        )
        raise
    except YAMLError as yaml_error:
        LOGGER.error(
            f"Failed to parse YAML file: {s3_details.get('object_key')} "
            f"from {s3_details.get('bucket_name')}, due to {yaml_error}"
        )
        raise


def start_executions(sfn_client, deployment_map):
    LOGGER.info(
        f"Invoking Pipeline Management State Machine ({PIPELINE_MANAGEMENT_STATEMACHINE})"
    )
    for pipeline in deployment_map.get("pipelines"):
        LOGGER.debug(f"Payload: {pipeline}")
        sfn_client.start_execution(
            stateMachineArn=PIPELINE_MANAGEMENT_STATEMACHINE,
            input=f"{json.dumps(pipeline)}",
        )


def lambda_handler(event, _):
    """Main Lambda Entry point"""
    output = event.copy()
    s3_resource = boto3.resource("s3")
    sfn_client = boto3.client("stepfunctions")
    s3_details = get_details_from_event(event)
    deployment_map = get_file_from_s3(s3_details, s3_resource)
    deployment_map["definition_bucket"] = s3_details.get("object_key")
    start_executions(sfn_client, deployment_map)
    return output
