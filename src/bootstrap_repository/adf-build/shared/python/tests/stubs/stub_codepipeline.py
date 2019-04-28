# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


"""
Stubs for testing codepipeline.py
"""

list_pipelines = {
    'pipelines': [
        {
            'name': 'my_pipeline',
            'version': 123,
            'created': 5678,
            'updated': 5678
        },
    ],
    'nextToken': 'string'
}

get_pipeline_state = {
    'pipelineName': 'string',
    'pipelineVersion': 123,
    'stageStates': [
        {
            'stageName': 'string',
            'inboundTransitionState': {
                'enabled': True,
                'lastChangedBy': 'string',
                'lastChangedAt': 2,
                'disabledReason': 'string'
            },
            'actionStates': [
                {
                    'actionName': 'string',
                    'currentRevision': {
                        'revisionId': 'string',
                        'revisionChangeId': 'string',
                        'created': 10
                    },
                    'latestExecution': {
                        'status': 'Succeeded',
                        'summary': 'string',
                        'lastStatusChange': 11,
                        'token': 'string',
                        'lastUpdatedBy': 'string',
                        'externalExecutionId': 'string',
                        'externalExecutionUrl': 'string',
                        'percentComplete': 123,
                        'errorDetails': {
                            'code': 'string',
                            'message': 'string'
                        }
                    },
                    'entityUrl': 'string',
                    'revisionUrl': 'string'
                },
            ],
            'latestExecution': {
                'pipelineExecutionId': 'string',
                'status': 'Succeeded'
            }
        },
    ],
    'created': 1234,
    'updated': 5678
}
