#Copyright 2019 Amazon.com, Inc.or its affiliates.All Rights Reserved.#SPDX - License - Identifier: MIT - 0

"""
Stubs for testing event.py
"""

config = {
    'main-notification-endpoint': [{
        'type': 'email',
        'target': 'jon.doe@email.com'
    }],
    'moves': [{
        'name': 'to-root',
        'action': 'remove-base'
    }]
}

event = {
    'version': '0',
    'id': 'fb25e4d2-1c1b-c410-8eb6-5471160373aa',
    'detail-type': 'AWS API Call via CloudTrail',
    'source': 'aws.organizations',
    'account': '111111111111',
    'time': '2019-02-25T13:53:53Z',
    'region': 'us-east-1',
    'resources': [],
    'detail': {
        'eventVersion': '1.04',
        'userIdentity': {
            'type': 'AssumedRole',
            'principalId': '123',
            'arn': 'arn:aws:sts::111111111111:assumed-role/somerole/some_name',
            'accountId': '111111111111',
            'accessKeyId': 'some_key',
            'sessionContext': {
                'attributes': {
                    'mfaAuthenticated': 'false',
                    'creationDate': '2019-02-25T07:28:32Z'
                },
                'sessionIssuer': {
                    'type': 'Role',
                    'principalId': 'AROAIAYD3G6ID4GFF4LXY',
                    'arn': 'arn:aws:iam::111111111111:role/somerole',
                    'accountId': '111111111111',
                    'userName': 'somerole'
                }
            }
        },
        'eventTime': '2019-02-25T13:53:53Z',
        'eventSource': 'organizations.amazonaws.com',
        'eventName': 'MoveAccount',
        'awsRegion': 'us-east-1',
        'sourceIPAddress': '72.21.198.65',
        'userAgent': 'AWS Organizations Console, aws-internal/3 aws-sdk-java/1.11.481 Linux/4.9.124-0.1.ac.198.71.329.metal1.x86_64 OpenJDK_64-Bit_Server_VM/25.192-b12 java/1.8.0_192',
        'requestParameters': {
            'accountId': '999999999999',
            'destinationParentId': 'ou-a9ny-ggggggg',
            'sourceParentId': 'r-a9xy'
        },
        'responseElements': None,
        'requestID': 'c9540550-3904-11e9-aa09-cf2b46b1104f',
        'eventID': '5ed57966-b36b-4baf-b3a0-2dc05805f51d',
        'eventType': 'AwsApiCall'
    }
}
