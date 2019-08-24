# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing s3.py
"""

s3_get_bucket_policy = {
    'Policy': {
        "Version": "2012-10-17",
        "Id": "Policy14564645656",
        "Statement": [{
            "Sid": "Stmt1445654645618",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::11111222222:root",
                    "arn:aws:iam::99999999999:root",
                    "SOME_RANDOM_DEAD_GUID"
                ]
            },
            "Action": "s3:Get*",
            "Resource": "arn:aws:s3:::bucket_name/abc/*"
        }]
    }
}
