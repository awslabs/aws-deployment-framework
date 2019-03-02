
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CodePipeline module used throughout the ADF
"""

from logger import configure_logger

LOGGER = configure_logger(__name__)


class CodePipeline():
    """Class used for modeling CodePipeline
    """

    def __init__(self, role):
        self.client = role.client('codepipeline')

    def get_pipeline_status(self, pipeline_name):
        """Gets a Pipeline Execution Status
        """
        try:
            response = self.client.get_pipeline_state(
                name=pipeline_name
            )

            return [i['actionStates'][0] for i in response.get(
                'stageStates', None)][0]['latestExecution']
        except BaseException:
            return None  # Pipeline does not exist

    def start_pipeline_execution(self, pipeline_name):
        self.client.start_pipeline_execution(
            name=pipeline_name
        )
