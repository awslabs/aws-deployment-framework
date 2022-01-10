"""
Pipeline Management Lambda Function
Stores pipeline input from prior funtion to S3.
"""

import os
import json

import boto3

from logger import configure_logger


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]


def upload_event_to_s3(s3, definition):
    pipeline_name = definition.get("input", {}).get("name")
    s3_object = s3.Object(S3_BUCKET_NAME, f"pipelines/{pipeline_name}/definition.json")
    s3_object.put(Body=json.dumps(definition).encode("UTF-8"))
    return f"{S3_BUCKET_NAME}/pipelines/{pipeline_name}/"


def lambda_handler(event, _):
    output = event.copy()
    s3 = boto3.resource("s3")
    location = upload_event_to_s3(s3, event)
    output["definition_location"] = location
    return output
