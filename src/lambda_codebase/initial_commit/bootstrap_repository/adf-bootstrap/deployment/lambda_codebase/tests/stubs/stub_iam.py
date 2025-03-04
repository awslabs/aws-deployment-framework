# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file
import os
from boto3.session import Session

REGION = os.getenv("AWS_REGION", "us-east-1")
PARTITION = Session().get_partition_for_region(REGION)

if PARTITION == "aws":
    test_region =  "eu-west-1"
else:
    test_region =  "cn-northwest-1"

"""
Stubs for testing iam.py
"""

get_role_policy = {
    'RoleName': 'string',
    'PolicyName': 'string',
    'PolicyDocument': {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "KMS",
                "Effect": "Allow",
                "Action": ["iam:ChangePassword"],
                "Resource": (
                    f"arn:{PARTITION}:kms:{test_region}:111111111111:key/existing_key"
                ),
            },
            {
                "Sid": "S3",
                "Effect": "Allow",
                "Action": "s3:ListAllMyBuckets",
                "Resource": [
                    f"arn:{PARTITION}:s3:::existing_bucket",
                    f"arn:{PARTITION}:s3:::existing_bucket/*",
                ],
            },
            {
                "Sid": "AssumeRole",
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": ['something'],
            },
        ]
    }
}