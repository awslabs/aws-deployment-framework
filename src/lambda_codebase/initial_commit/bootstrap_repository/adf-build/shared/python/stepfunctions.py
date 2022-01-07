# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Step Functions module used throughout the ADF
"""

import json
from time import sleep
from logger import configure_logger
from partition import get_partition

LOGGER = configure_logger(__name__)


class StepFunctions:
    """
    Class used for modeling Step Functions
    """

    def __init__(
            self,
            role,
            deployment_account_id,
            deployment_account_region,
            regions,
            account_ids=None,
            full_path=None,
            update_pipelines_only=0,
            error=0
        ):
        self.deployment_account_region = deployment_account_region
        self.client = role.client(
            'stepfunctions',
            region_name=self.deployment_account_region
        )
        self.regions = regions
        self.deployment_account_id = deployment_account_id
        self.update_pipelines_only = update_pipelines_only
        self.account_ids = account_ids
        self.execution_arn = None
        self.full_path = full_path
        self.execution_status = None
        self.error = error

    def execute_statemachine(self):
        """
        Main entry to executed state machine in Deployment Account
        """
        self._start_statemachine()
        self._wait_state_machine_execution()

    def _start_statemachine(self):
        """
        Executes the Update Cross Account IAM Step Function in the Deployment Account
        """
        partition = get_partition(self.deployment_account_region)

        self.execution_arn = self.client.start_execution(
            stateMachineArn=(
                f"arn:{partition}:states:{self.deployment_account_region}:"
                f"{self.deployment_account_id}:stateMachine:EnableCrossAccountAccess"
            ),
            input=json.dumps({
                "deployment_account_region": self.deployment_account_region,
                "deployment_account_id": self.deployment_account_id,
                "account_ids": self.account_ids,
                "regions": self.regions,
                "full_path": self.full_path,
                "update_only": self.update_pipelines_only,
                "error": self.error
            })
        ).get('executionArn')

        self._fetch_statemachine_status()

    @property
    def execution_status(self):
        """
        Returns the status of the state machine
        """
        return self._execution_status

    @execution_status.setter
    def execution_status(self, execution_status):
        """
        Set the status of the state machine
        """
        self._execution_status = execution_status

    def _fetch_statemachine_status(self):
        """
        Get the current status of the state machine
        """
        execution = self.client.describe_execution(
            executionArn=self.execution_arn
        )
        self._execution_status = execution.get('status', None)

    # Is there a legit waiter for this?
    def _wait_state_machine_execution(self):
        """
        Waits until the state machine is complete
        """
        while self.execution_status == 'RUNNING':
            self._fetch_statemachine_status()
            sleep(10)  # Wait for 10 seconds and check the status again

        if self.execution_status in ('FAILED', 'ABORTED', 'TIMED_OUT'):
            raise Exception(
                f'State Machine on Deployment account {self.deployment_account_id} '
                f'has status: {self.execution_status}, see logs'
            )
