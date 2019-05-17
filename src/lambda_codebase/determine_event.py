# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Initial event object determination function
"""

import os
import boto3

from parameter_store import ParameterStore
from cache import Cache
from event import Event
from organizations import Organizations

REGION_DEFAULT = os.environ["AWS_REGION"]

def lambda_handler(event, _):
    parameters = ParameterStore(region=REGION_DEFAULT, role=boto3)
    account_id = event.get(
        'detail').get(
            'requestParameters').get('accountId')
    organizations = Organizations(role=boto3, account_id=account_id)
    parsed_event = Event(
        event=event,
        parameter_store=parameters,
        organizations=organizations,
        account_id=account_id
    )
    cache = Cache()

    account_path = "ROOT" if parsed_event.moved_to_root else parsed_event.organizations.build_account_path(
        parsed_event.destination_ou_id,
        [],  # Initial empty array to hold OU Path,
        cache
    )

    if parsed_event.moved_to_root or parsed_event.moved_to_protected:
        return parsed_event.create_output_object(account_path)

    parsed_event.set_destination_ou_name()

    return parsed_event.create_output_object(account_path)
