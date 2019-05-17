# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file


stub_approval_event = {
    'Records': [{
        'EventSource': 'aws:sns',
        'EventVersion': '1.0',
        'EventSubscriptionArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
        'Sns': {
            'Type': 'Notification',
            'MessageId': '1',
            'TopicArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
            'Subject': 'APPROVAL NEEDED: AWS CodePipeline adf-pipeline-sample-vpc for action Approve',
            'Message': '{"region":"eu-central-1","consoleLink":"https://console.aws.amazon.com","approval":{"pipelineName":"adf-pipeline-sample-vpc","stageName":"approval-stage-1","actionName":"Approve","token":"fa777887-41dc-4ac4-8455-a209a93c76b9","expires":"2019-03-17T11:08Z","externalEntityLink":null,"approvalReviewLink":"https://console.aws.amazon.com/codepipeline/"}}',
            'Timestamp': '3000-03-10T11:08:34.673Z',
            'SignatureVersion': '1',
            'Signature': '1',
            'SigningCertUrl': 'https://sns.eu-central-1.amazonaws.com/SimpleNotificationService',
            'UnsubscribeUrl': 'https://sns.eu-central-1.amazonaws.com',
            'MessageAttributes': {}
        }
    }]
}

stub_bootstrap_event = {
    'Records': [{
        'EventSource': 'aws:sns',
        'EventVersion': '1.0',
        'EventSubscriptionArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
        'Sns': {
            'Type': 'Notification',
            'MessageId': '1',
            'TopicArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
            'Subject': 'AWS Deployment Framework Bootstrap',
            'Message': 'Account 1111111 has now been bootstrapped into banking/production',
            'Timestamp': '3000-03-10T11:08:34.673Z',
            'SignatureVersion': '1',
            'Signature': '1',
            'SigningCertUrl': 'https://sns.eu-central-1.amazonaws.com/SimpleNotificationService',
            'UnsubscribeUrl': 'https://sns.eu-central-1.amazonaws.com',
            'MessageAttributes': {}
        }
    }]
}

stub_failed_pipeline_event = {
    'Records': [{
        'EventSource': 'aws:sns',
        'EventVersion': '1.0',
        'EventSubscriptionArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
        'Sns': {
            'Type': 'Notification',
            'MessageId': '1',
            'TopicArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
            'Subject': None,
            'Message': '{"version":"0","id":"1","detail-type":"CodePipeline Pipeline Execution State Change","source":"aws.codepipeline","account":"2","time":"3000-03-10T11:09:38Z","region":"eu-central-1","resources":["arn:aws:codepipeline:eu-central-1:999999:adf-pipeline-sample-vpc"],"detail":{"pipeline":"adf-pipeline-sample-vpc","execution-id":"1","state":"FAILED","version":9.0}}',
            'Timestamp': '2019-03-10T11:09:49.953Z',
            'SignatureVersion': '1',
            'Signature': '2',
            'SigningCertUrl': 'https://sns.eu-central-1.amazonaws.com/SimpleNotificationService',
            'UnsubscribeUrl': 'https://sns.eu-central-1.amazonaws.com',
            'MessageAttributes': {}
        }
    }]
}

stub_failed_bootstrap_event = {
    'Records': [{
        'EventSource': 'aws:sns',
        'EventVersion': '1.0',
        'EventSubscriptionArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
        'Sns': {
            'Type': 'Notification',
            'MessageId': '1',
            'TopicArn': 'arn:aws:sns:eu-central-1:9999999:adf-pipeline-sample-vpc-PipelineSNSTopic-example',
            'Subject': 'Failure - AWS Deployment Framework Bootstrap',
            'Message': '{"Error":"Exception","Cause":"{\\"errorMessage\\": \\"CloudFormation Stack Failed - Account: 111 Region: eu-central-1 Status: ROLLBACK_IN_PROGRESS\\", \\"errorType\\": \\"Exception\\", \\"stackTrace\\": [[\\"/var/task/wait_until_complete.py\\", 99, \\"lambda_handler\\", \\"status))\\"]]}"}',
            'Timestamp': '2019-03-10T11:09:49.953Z',
            'SignatureVersion': '1',
            'Signature': '2',
            'SigningCertUrl': 'https://sns.eu-central-1.amazonaws.com/SimpleNotificationService',
            'UnsubscribeUrl': 'https://sns.eu-central-1.amazonaws.com',
            'MessageAttributes': {}
        }
    }]
}