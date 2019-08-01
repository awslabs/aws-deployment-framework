#!/usr/bin/env python3

from aws_cdk import core
from cdk_stacks.main import PipelineMainStack

# params will come from the deployment_map for this specific pipeline
params = {
            "name": "sample-iam",
            "type": "cc-cloudformation",
            "regions": ["eu-central-1"],
            "params": [
                {
                    "SourceAccountId": 228171733466
                },
                {
                    "NotificationEndpoint": "bundyf@amazon.com"
                }
            ],
            "targets": [
                {
                    "path": "/banking/testing",
                    "name": "testing"
                },
                {
                    "path": "/banking/production",
                    "name": "prod"
                }
            ]
}

app = core.App()
PipelineMainStack(app, "pipeline-types", params)

app.synth()
