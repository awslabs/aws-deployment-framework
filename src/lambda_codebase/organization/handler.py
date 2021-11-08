# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Organization Handler that is called when ADF is installed to create the organization if required
"""

try:
    from main import lambda_handler # pylint: disable=unused-import
except Exception as err: # pylint: disable=broad-except
    import os
    import logging
    from urllib.request import Request, urlopen
    import json

    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(os.environ.get("ADF_LOG_LEVEL", logging.INFO))

    def lambda_handler(event, _context, prior_error=err):
        payload = dict(
            LogicalResourceId=event["LogicalResourceId"],
            PhysicalResourceId=event.get("PhysicalResourceId", "NOT_YET_CREATED"),
            Status="FAILED",
            RequestId=event["RequestId"],
            StackId=event["StackId"],
            Reason=str(prior_error),
        )
        with urlopen(
            Request(
                event["ResponseURL"],
                data=json.dumps(payload).encode(),
                headers={"content-type": ""},
                method="PUT",
            )
        ) as response:
            response_body = response.read().decode("utf-8")
            LOGGER.debug(
                "Response: %s",
                response_body,
            )
