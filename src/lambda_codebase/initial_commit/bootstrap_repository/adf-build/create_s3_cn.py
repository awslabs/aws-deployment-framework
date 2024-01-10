# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Main entry point for create_s3_cn.py execution which
is executed from within AWS CodeBuild in the management account
"""
import os
import boto3
from logger import configure_logger
from cloudformation import CloudFormation

REGION_DEFAULT = os.environ["AWS_REGION"]
ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
LOGGER = configure_logger(__name__)

def _create_s3_bucket(bucket_name):
    try:
        LOGGER.info(f"Deploy S3 bucket {bucket_name}...")
        extra_deploy_region = "cn-northwest-1"
        template_path = "adf-build/cn_northwest_bucket.yml"
        stack_name = 'adf-regional-base-china-bucket'
        parameters= [
                {
                    'ParameterKey': 'BucketName',
                    'ParameterValue': bucket_name,
                    'UsePreviousValue': False,
                },          
            ]
        cloudformation = CloudFormation(
            region=extra_deploy_region,
            deployment_account_region=extra_deploy_region,
            role=boto3,
            wait=True,
            stack_name=stack_name,
            account_id=ACCOUNT_ID,
            parameters = parameters,
            local_template_path=template_path
        )
        cloudformation.create_stack()
    except Exception as error:
        LOGGER.error(f"Failed to process _create_s3_bucket, error:\n {error}")
        exit(1)

def main():
    bucket_name = f"adf-china-bootstrap-cn-northwest-1-{ACCOUNT_ID}"
    _create_s3_bucket(bucket_name)

if __name__ == '__main__':
    main()
