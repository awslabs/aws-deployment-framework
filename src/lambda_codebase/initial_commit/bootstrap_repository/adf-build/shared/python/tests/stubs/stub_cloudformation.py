# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing cloudformation.py
"""

describe_stack = {
    'Stacks': [{
        'Outputs': [
            {
                'OutputKey': "DeploymentFrameworkRegionalKMSKey",
                'OutputValue': "some_key_arn"
            }, {
                'OutputKey': "DeploymentFrameworkRegionalS3Bucket",
                'OutputValue': "some_bucket_name"
            }
        ],
        'StackStatus': 'CREATE_IN_PROGRESS'
    }]
}

list_stacks = {
    'StackSummaries': [
        {
            # Should be filtered out, not a ADF base stack
            'StackName': 'adf-different-stack',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, not deprecated
            'StackName': 'adf-global-base-bootstrap',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, but should only exist in non global regions.
            'StackName': 'adf-regional-base-bootstrap',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, but should only exist in the global deployment
            # account.
            'StackName': 'adf-global-base-deployment',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, but should only exist in the global deployment
            # account.
            'StackName': (
                'adf-global-base-deployment-PipelineManagementApplication-156BTR33REGR'
            ),
            'StackStatus': 'CREATE_COMPLETE',
            'ParentId': 'Unique-Stack-Id',
        },
        {
            # Should be deprecated when deleting deprecated base stacks
            'StackName': 'adf-global-base-deployment-SomeOtherStack',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be deprecated when deleting deprecated base stacks
            'StackName': 'adf-global-base-bootstrap-SomeNestedStack',
            'StackStatus': 'CREATE_COMPLETE',
            'ParentId': 'Unique-Stack-Id',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, but should only exist in the global management
            # account.
            'StackName': 'adf-global-base-adf-build',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Should be filtered out when deleting deprecated base stacks
            # This is current, not deprecated
            'StackName': 'adf-global-base-iam',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            'StackName': 'adf-global-base-dev',
            'StackStatus': 'CREATE_COMPLETE',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            # Note the stack status, this should print a warning instead
            # of deleting it.
            'StackName': 'adf-global-base-test',
            'StackStatus': 'CREATE_FAILED',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            # Note the stack status, this should print a warning instead
            # of deleting it.
            'StackName': 'adf-global-base-acceptance',
            'StackStatus': 'ROLLBACK_FAILED',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            'StackName': 'adf-global-base-prod',
            'StackStatus': 'UPDATE_COMPLETE',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            # Note the stack status, this should print a warning instead
            # of deleting it.
            'StackName': 'adf-global-base-some-ou',
            'StackStatus': 'CREATE_IN_PROGRESS',
        },
        {
            # Using a deprecated OU name in the base stack name, should be
            # deleted when deleting deprecated base stacks.
            # Note the stack status, this should print a warning instead
            # of deleting it.
            'StackName': 'adf-global-base-some-old-ou',
            'StackStatus': 'DELETE_COMPLETE',
        },
    ],
    'NextToken': 'string',
}
