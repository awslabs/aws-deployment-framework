# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        "Statement": [{
                "Sid": "KMS",
                "Effect": "Allow",
                "Action": ["iam:ChangePassword"],
                "Resource": ["some_service:some_action"]
            },
            {
                "Sid": "S3",
                "Effect": "Allow",
                "Action": "s3:ListAllMyBuckets",
                "Resource": ["some_service:some_action"]
            },
            {
                "Sid": "AssumeRole",
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": ['something']
            }
        ]
    }
}
