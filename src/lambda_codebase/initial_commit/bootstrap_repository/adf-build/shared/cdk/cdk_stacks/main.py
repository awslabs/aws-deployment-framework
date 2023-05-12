# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This is the main construct file file for PipelineStack
"""

from aws_cdk import Stack
from constructs import Construct
from logger import configure_logger

from cdk_stacks.adf_default_pipeline import (
    generate_adf_default_pipeline as generate_default_pipeline,
    PIPELINE_TYPE as DEFAULT_PIPELINE,
)

LOGGER = configure_logger(__name__)


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_input: dict,
        **kwargs,
    ) -> None:  # pylint: disable=R0912, R0915
        """
        Initialize the pipeline stack
        """
        super().__init__(
            scope,
            stack_input["pipeline_input"]['name'],
            **kwargs,
        )
        LOGGER.info(
            'Pipeline creation/update of %s commenced',
            stack_input['pipeline_input']['name'],
        )
        pipeline_type = (
            stack_input['pipeline_input']
            .get('params', {})
            .get('pipeline_type', DEFAULT_PIPELINE)
            .lower()
        )

        self.generate_pipeline(pipeline_type, stack_input)

    def generate_pipeline(self, pipeline_type, stack_input):
        if pipeline_type == DEFAULT_PIPELINE:
            generate_default_pipeline(self, stack_input)
        else:
            raise ValueError(f'{pipeline_type} is not defined in main.py')
