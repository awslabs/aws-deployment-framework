# pylint: skip-file

# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Executes as part of the bootstrap process
for when the Deployment Account is initially
created and moved into its OU. This step creates
a AWS CloudFormation stack on the Master account (containing IAM roles)
In the same region defined as the Deployment Account
Region that allows the Deployment Account access to
query AWS Organizations when it needs to create pipelines.
"""

import os
import boto3

from cloudformation import CloudFormation
from s3 import S3

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
MASTER_ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
REGION_DEFAULT = os.environ["AWS_REGION"]


def lambda_handler(event, _):
    s3 = S3(region=REGION_DEFAULT, bucket=S3_BUCKET)

    cloudformation = CloudFormation(
        region=event['deployment_account_region'],
        deployment_account_region=event['deployment_account_region'],
        role=boto3,
        wait=True,
        stack_name=None,
        s3=s3,
        s3_key_path='adf-build',
        account_id=event["account_id"]
    )
    cloudformation.create_stack()

    return event
