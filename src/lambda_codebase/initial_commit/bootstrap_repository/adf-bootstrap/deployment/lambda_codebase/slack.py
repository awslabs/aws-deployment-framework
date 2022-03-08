# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This Functions handles Slack Notifications for all pipelines
if a slack channel has been defined as a NotificationEndpoint
"""

import os
import json
import urllib
import boto3

from parameter_store import ParameterStore


def extract_pipeline(message):
    """
    Try extract the pipeline name from the message (approval/success/failure)
    otherwise if message was a string (bootstrap events) then set its value to main
    since we want to access the main notification endpoint for bootstrap events
    """
    try:
        name = message.get('approval', {}).get('pipelineName', None) or message.get("detail", {}).get("pipeline", None)
        return {
            "name": name.split(str(os.environ.get("ADF_PIPELINE_PREFIX")))[-1],
            "state": message.get("detail", {}).get("state"),
            "time": message.get("time"),
            "account_id": message.get("account")
        }
    except AttributeError:
        return {
            "name": message.split(
                str(os.environ.get("ADF_PIPELINE_PREFIX"))
            )[-1].split(' from account')[0],
            "state": message.split('has ')[-1].split(' at')[0],
            "time": message.split('at ')[-1],
            "account_id": message.split('account ')[-1].split(' has')[0]
        }


def is_approval(message):
    """
    Determines if the message sent in was for an approval action
    """
    if isinstance(message, str):
        return False
    return message.get('approval', None)


def is_bootstrap(event):
    """
    Determines if the message sent in was for an bootstrap action -
    Bootstrap (success) events are always just strings so loading it as json should
    raise a ValueError
    """
    try:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        if isinstance(message, dict):
            if message.get('Error'):
                return True
        return False
    except ValueError:
        return True


def extract_message(event):
    """
    Takes the message out of the incoming event and attempts to load it into JSON
    This will raise a ValueError (JSONDecode) on bootstrap and thus we should
    return the raw message.
    """
    message = event['Records'][0]['Sns']['Message']
    try:
        return json.loads(message)
    except ValueError:
        return message


def create_approval(channel, message):
    """
    Creates a dict that will be sent to send_message for approvals
    """
    return {
        "text": (
            f":clock1: Pipeline {message['approval']['pipelineName']} "
            f"in {message['approval']['customData']} requires approval"
        ),
        "channel": channel,
        "attachments": [
            {
                "fallback": f"Approve or Deny Deployment at {message['consoleLink']}",
                "actions": [
                    {
                        "type": "button",
                        "text": "Approve or Deny Deployment",
                        "url": str(message["consoleLink"])
                    }
                ]
            }
        ]
    }


def create_pipeline_message_text(channel, pipeline):
    """
    Creates a dict that will be sent to send_message for pipeline success or failures
    """
    emote = ":red_circle:" if pipeline.get("state") == "FAILED" else ":white_check_mark:"
    return {
        "channel": channel,
        "text": (
            f"{emote} Pipeline {pipeline['name']} on {pipeline['account_id']} "
            f"has {pipeline['state']}"
        ),
    }


def create_bootstrap_message_text(channel, message):
    """
    Creates a dict that will be sent to send_message for bootstrapping completion
    """
    if isinstance(message, dict):
        if message.get('Error'):
            message = json.loads(message.get('Cause')).get('errorMessage')

    emote = ":red_circle:" if any(x in message for x in ['error', 'Failed']) else ":white_check_mark:"
    return {
        "channel": channel,
        "text": f"{emote} {message}"
    }


def send_message(url, payload):
    """
    Sends the message to the designated slack webhook
    """
    params = json.dumps(payload).encode('utf8')
    req = urllib.request.Request(
        url,
        data=params,
        headers={'content-type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        return response.read()


def lambda_handler(event, _):
    message = extract_message(event)
    pipeline = extract_pipeline(message)
    parameter_store = ParameterStore(os.environ["AWS_REGION"], boto3)
    secrets_manager = boto3.client('secretsmanager', region_name=os.environ["AWS_REGION"])
    channel = parameter_store.fetch_parameter(
        name=f'/notification_endpoint/{pipeline["name"]}',
        with_decryption=False,
    )
    # All slack url's must be stored in /adf/slack/channel_name since ADF only
    # has access to the /adf/ prefix by default
    url = json.loads(secrets_manager.get_secret_value(
        SecretId=f'/adf/slack/{channel}'
    )['SecretString'])
    if is_approval(message):
        send_message(url[channel], create_approval(channel, message))
        return
    if is_bootstrap(event):
        send_message(url[channel], create_bootstrap_message_text(channel, message))
        return
    send_message(url[channel], create_pipeline_message_text(channel, pipeline))
    return
