#!/usr/bin/env python3

import os
import boto3

from aws_cdk import core
from parameter_store import ParameterStore
from cdk_stacks.main import PipelineMainStack

# params will come from the deployment_map for this specific pipeline
params = {
    "pipeline_name": "tests",
    "stages": [1, 2],
    "regions": ["eu-west-1"],
    "parameter_store_client": ParameterStore(os.environ["ADF_DEPLOYMENT_REGION"], boto3)
}

print(params)
app = core.App()
PipelineMainStack(app, "pipeline-types", params)

app.synth()
