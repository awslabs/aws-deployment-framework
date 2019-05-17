# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Account handler that is called when ADF is installed to initially create the deployment account if required
"""

try:
    from main import lambda_handler # pylint: disable=unused-import
except Exception as err:  # pylint: disable=broad-except
    from urllib.request import Request, urlopen
    import json

    def lambda_handler(event, _context, prior_error=err):
        response = dict(
            LogicalResourceId=event["LogicalResourceId"],
            PhysicalResourceId=event.get("PhysicalResourceId", "NOT_YET_CREATED"),
            Status="FAILED",
            RequestId=event["RequestId"],
            StackId=event["StackId"],
            Reason=str(prior_error),
        )
        urlopen(
            Request(
                event["ResponseURL"],
                data=json.dumps(response).encode(),
                headers={"content-type": ""},
                method="PUT",
            )
        )
