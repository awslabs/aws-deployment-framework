
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CodePipeline module used throughout the ADF
"""

from logger import configure_logger

LOGGER = configure_logger(__name__)


class CodePipeline():
    """Class used for modeling CodePipeline
    """

    def __init__(self, role, region):
        self.client = role.client('codepipeline', region_name=region)

    def get_pipeline_status(self, pipeline_name):
        """Gets a Pipeline Execution Status
        """
        try:
            response = self.client.get_pipeline_state(
                name=pipeline_name
            )

            return [i for i in response.get(
                'stageStates')][0]['latestExecution']['status']
        except KeyError:
            LOGGER.error('Pipeline status for %s could not be determined', pipeline_name)
            return None

    def start_pipeline_execution(self, pipeline_name):
        self.client.start_pipeline_execution(
            name=pipeline_name
        )
