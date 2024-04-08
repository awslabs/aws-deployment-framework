# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Describe CodePipeline trigger.

This script will retrieve the trigger for the given CodePipeline execution.
It also allows you to match it against a specific trigger that you expect and
return an exit code if it did not match.

Usage:
    describe_codepipeline_trigger.py
            [--should-match <trigger_type>]
            [--json]
            [-v... | --verbose...]
            CODEPIPELINE_NAME
            EXECUTION_ID

    describe_codepipeline_trigger.py -h | --help

    describe_codepipeline_trigger.py --version

Arguments:
    CODEPIPELINE_NAME
                The CodePipeline name of the pipeline to check.

    EXECUTION_ID
                The CodePipeline Execution Id that we want to check.

Options:
    -h, --help  Show this help message.

    --json      Return the trigger type and details as a JSON object.
                An example object:
                {
                    "trigger_type": "StartPipelineExecution or other",
                    "trigger_detail": "..."
                }

    --should-match <trigger_type>
                When set, it will stop with exit code 0 if it matches the
                expected trigger. If it does not match the trigger, it will
                stop with exit code 1.
                Trigger type can be: 'CreatePipeline',
                'StartPipelineExecution', 'PollForSourceChanges', 'Webhook',
                'CloudWatchEvent', or 'PutActionRevision'.

    -v, --verbose
                Show verbose logging information.
"""

import os
import sys
from typing import Any, Optional, TypedDict
import json
import logging
import boto3
from docopt import docopt


ADF_VERSION = os.environ.get("ADF_VERSION")
ADF_LOG_LEVEL = os.environ.get("ADF_LOG_LEVEL", "INFO")

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(ADF_LOG_LEVEL)


class TriggerData(TypedDict):
    """
    Trigger Data Class.
    """
    trigger_type: str
    trigger_detail: str


def fetch_codepipeline_execution_trigger(
    cp_client: Any,
    codepipeline_name: str,
    execution_id: str,
) -> Optional[TriggerData]:
    """
    Fetch the CodePipeline Execution Trigger that matches
    the requested parameters.

    Args:
        cp_client (boto3.client): The CodePipeline Boto3 client.

        codepipeline_name (str): The CodePipeline name.

        execution_id (str): The CodePipeline Execution id.

    Returns:
        TriggerData: The trigger type and trigger detail if found.

        None: if it was not found.
    """
    paginator = cp_client.get_paginator('list_pipeline_executions')
    response_iterator = paginator.paginate(pipelineName=codepipeline_name)
    for page in response_iterator:
        for execution in page['pipelineExecutionSummaries']:
            if execution['pipelineExecutionId'] == execution_id:
                return {
                    "trigger_type": execution['trigger']['triggerType'],
                    "trigger_detail": execution['trigger']['triggerDetail'],
                }
    return None


def main():
    """Main function to describe the codepipeline trigger """
    options = docopt(__doc__, version=ADF_VERSION, options_first=True)

    # In case the user asked for verbose logging, increase
    # the log level to debug.
    if options["--verbose"] > 0:
        LOGGER.setLevel(logging.DEBUG)
    if options["--verbose"] > 1:
        logging.basicConfig(level=logging.INFO)
    if options["--verbose"] > 2:
        # Also enable DEBUG mode for other libraries, like boto3
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug("Input arguments: %s", options)

    codepipeline_name = options.get('CODEPIPELINE_NAME')
    execution_id = options.get('EXECUTION_ID')
    should_match_type = options.get('--should-match')
    output_in_json = options.get('--json')

    cp_client = boto3.client("codepipeline")
    trigger = fetch_codepipeline_execution_trigger(
        cp_client,
        codepipeline_name,
        execution_id,
    )

    if trigger is None:
        LOGGER.error(
            "Could not find execution %s in the %s pipeline.",
            execution_id,
            codepipeline_name,
        )
        sys.exit(2)

    if output_in_json:
        print(json.dumps(trigger))
    else:
        print(trigger['trigger_type'])

    if should_match_type and trigger['trigger_type'] != should_match_type:
        sys.exit(1)


if __name__ == "__main__":
    main()
