# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import uuid
from decimal import Decimal


def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    else:
        return obj


class Stepfunction:
    """Class to handle Custom Stepfunction methods"""

    def __init__(
        self,
        session,
        LOGGER
    ):
        self.logger = LOGGER
        self.session = session

    def get_stepfunction_client(self):
        return self.session.client("stepfunctions")

    def invoke_sfn_execution(
            self,
            sfn_arn,
            input: dict,
            execution_name=None):
        try:
            state_machine_arn = sfn_arn
            sfn_client = self.get_stepfunction_client()

            if not execution_name:
                execution_name = str(uuid.uuid4())
            event_body = json.dumps(convert_decimals(input), indent=2)
            response = sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=event_body
            )
        except Exception as e:
            msg = f"Couldn't invoke stepfunction {sfn_arn}, error: {e}."
            self.logger.error(msg)
            raise
        return response, execution_name
