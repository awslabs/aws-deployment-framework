#!/usr/bin/env python3

from aws_cdk import core
from cdk_stacks.main import PipelineStack

# params will come from the deployment_map for this specific pipeline
map_params = {
    'environments': {
        'targets': [
            [{
                'name': 'banking-testing',
                'id': '130330464033',
                'path': '/banking/testing',
                'regions': ['eu-central-1'],
                'params': {},
                'step_name': ''
            }, {
                'name': 'bundyf-testing',
                'id': '728154317245',
                'path': '/banking/testing',
                'regions': ['eu-central-1'],
                'params': {},
                'step_name': ''
            }],
            [{
                'name': 'approval',
                'id': 'approval',
                'path': 'approval',
                'regions': ['eu-central-1'],
                'params': {},
                'step_name': ''
            }],
            [{
                'name': 'bundyf-prod',
                'id': '944504663010',
                'path': '/banking/production',
                'regions': ['eu-central-1'],
                'params': {},
                'step_name': ''
            }]
        ]
    },
    'name': 'sample-iam',
    'notification_endpoint': 'bundyf@amazon.com',
    'top_level_regions': [],
    'regions': ['eu-central-1'],
    "type": {
        "source": {
            "name": "codecommit",
            "account_id": 228171733466
        },
        "build": {
            "name": "codebuild"
        },
        "deploy": {
            "name": "cloudformation"
        }
    },
    'deployment_account_region': 'eu-central-1',
    'deployment_role': None,
    'action': '',
    'contains_transform': '',
    'completion_trigger': {}
}

app = core.App()
PipelineStack(app, "pipeline-types", map_params)

app.synth()
