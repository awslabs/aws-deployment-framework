# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

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
                    "arn:aws:kms:eu-west-1:111111111111:key/existing_key"
                ),
            },
            {
                "Sid": "S3",
                "Effect": "Allow",
                "Action": "s3:ListAllMyBuckets",
                "Resource": [
                    "arn:aws:s3:::existing_bucket",
                    "arn:aws:s3:::existing_bucket/*",
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
