# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

"""
Stubs for testing KMS
"""

kms_get_policy = {
    'Policy': '{\n  "Version" : "2012-10-17",\n  "Id" : "key-default-1",\n  "Statement" : [ {\n    "Sid" : "Enable IAM User Permissions",\n    "Effect" : "Allow",\n    "Principal" : {\n      "AWS" : ["arn:aws:iam::111111111111:root"]\n    },\n    "Action" : "kms:*",\n    "Resource" : "*"\n  } ]\n}',
}
