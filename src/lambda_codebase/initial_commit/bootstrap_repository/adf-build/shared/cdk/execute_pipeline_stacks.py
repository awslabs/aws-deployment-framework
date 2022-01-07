#!/usr/bin/env python3

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the pipeline CloudFormation stacks via the AWS CDK
"""

import random
import os
import glob
import time
from thread import PropagatingThread
import boto3

from s3 import S3
from logger import configure_logger
from cloudformation import CloudFormation


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
MASTER_ACCOUNT_ID = os.environ["MASTER_ACCOUNT_ID"]
ORGANIZATION_ID = os.environ["ORGANIZATION_ID"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
ADF_PIPELINE_PREFIX = os.environ["ADF_PIPELINE_PREFIX"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]


def upload_pipeline(template_path, name, s3):
    """
    Responsible for uploading the object (global.yml) to S3
    and returning the URL that can be referenced in the CloudFormation
    create_stack call.
    """
    s3_object_path = s3.put_object(f"pipelines/{name}/global.yml", template_path)
    LOGGER.debug('Uploaded Pipeline Template %s to S3', s3_object_path)
    return s3_object_path


def worker_thread(template_path, name, s3):
    s3_object_path = upload_pipeline(template_path, name, s3)
    cloudformation = CloudFormation(
        region=DEPLOYMENT_ACCOUNT_REGION,
        deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
        role=boto3,
        template_url=s3_object_path,
        parameters=[],
        wait=True,
        stack_name=f"{ADF_PIPELINE_PREFIX}{name}",
        s3=None,
        s3_key_path=None,
        account_id=DEPLOYMENT_ACCOUNT_ID
    )
    cloudformation.create_stack()


def main():
    LOGGER.info('ADF Version %s', ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)
    s3 = S3(
        DEPLOYMENT_ACCOUNT_REGION,
        S3_BUCKET_NAME
    )
    threads = []
    template_paths = glob.glob("cdk.out/*.template.json")
    for counter, template_path in enumerate(template_paths):
        # The Stack name only. No extension and no .template
        name = os.path.splitext(template_path.split('/')[-1].split('.template')[0])[0]
        with open(template_path, encoding='utf-8') as _template_path:
            thread = PropagatingThread(target=worker_thread, args=(
                template_path,
                name,
                s3
            ))
            thread.start()
            threads.append(thread)
            batch_mod = counter % 10
            if batch_mod == 9: # 9 meaning we have hit a set of 10 threads since n % 10
                delay = random.randint(5, 11)
                LOGGER.debug('Waiting for %s seconds before starting next batch of 10 threads.', delay)
                time.sleep(delay)

    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
