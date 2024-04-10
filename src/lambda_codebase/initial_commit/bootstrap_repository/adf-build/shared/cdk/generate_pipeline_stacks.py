#!/usr/bin/env python3

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
This file is pulled into CodeBuild containers
and used to build the pipeline CloudFormation stacks via the AWS CDK
"""

import glob
import os
import json

# CDK Specific
from aws_cdk import App, BootstraplessSynthesizer
from cdk_stacks.main import PipelineStack

from logger import configure_logger

LOGGER = configure_logger(__name__)
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]


def main():
    LOGGER.info("ADF Version %s", ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)
    _templates = glob.glob("cdk_inputs/*.json")
    for template_path in _templates:
        with open(template_path, encoding="utf-8") as template:
            stack_input = json.load(template)
            app = App()
            PipelineStack(
                app,
                stack_input,
                synthesizer=BootstraplessSynthesizer(),
            )
            app.synth()


if __name__ == "__main__":
    main()
