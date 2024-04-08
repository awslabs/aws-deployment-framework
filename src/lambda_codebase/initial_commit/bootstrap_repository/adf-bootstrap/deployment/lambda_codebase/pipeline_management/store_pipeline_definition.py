# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Pipeline Management Lambda Function
Stores pipeline input from prior function to S3.
"""

import os
import json

import boto3

from logger import configure_logger


LOGGER = configure_logger(__name__)
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]


def upload_event_to_s3(s3_resource, definition):
    """
    Upload the event received to the Pipeline Definition Bucket.

    Args:
        s3_resource (boto3.S3.resource): The S3 resource.
        definition (any): The pipeline definition, input and other data
            related to the pipeline to store.

    Returns:
        str: The location where the definition is stored in the S3 bucket.
    """
    pipeline_name = definition.get("pipeline_input", {}).get("name")
    s3_object = s3_resource.Object(
        S3_BUCKET_NAME,
        f"pipelines/{pipeline_name}/definition.json",
    )
    s3_object.put(Body=json.dumps(definition).encode("UTF-8"))
    return f"{S3_BUCKET_NAME}/pipelines/{pipeline_name}/"


def lambda_handler(event, _):
    """
    Writes the pipeline definition to S3.

    Args:
        event (dict): The input event, that is also returned as the output.

    Returns:
        dict: The input event + definition_location.
    """
    output = event.copy()
    s3_resource = boto3.resource("s3")

    location = upload_event_to_s3(s3_resource, event)

    output["definition_location"] = location
    return output
