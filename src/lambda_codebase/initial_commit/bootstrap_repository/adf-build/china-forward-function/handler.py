# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The forward function will forward events to the target SFN.
"""

import logging
import os

import boto3
from stepfunction_helper import Stepfunction

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(os.environ.get("ADF_LOG_LEVEL", logging.INFO))
SFN_ARN = os.getenv("SFN_ARN", "")
sfn_name = SFN_ARN.split(':')[-1]


def lambda_handler(event, context):
    LOGGER.debug(event)
    if "source" in event and event["source"] == "aws.organizations":
        session = boto3.session.Session(region_name="cn-north-1")
        sfn_instance = Stepfunction(session, LOGGER)
        _, state_name = sfn_instance.invoke_sfn_execution(
            sfn_arn=SFN_ARN,
            input=event,
        )
        LOGGER.info(f"Successfully invoke sfn {sfn_name} with statemachine name {state_name}.")
