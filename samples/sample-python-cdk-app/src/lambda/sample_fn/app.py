# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Sample "Hello World" Lambda function.

This handler demonstrates that the Lambda is packaged with its own
dependencies (declared in this folder's requirements.txt) - independently of
both the CDK application and ADF. It uses AWS Lambda Powertools for structured
logging and X-Ray tracing to show real third-party dependencies being bundled.
"""

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Return a simple "Hello World" response."""
    logger.info("Sample Hello World function invoked")
    return {
        "statusCode": 200,
        "body": "Hello World",
    }
