#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
retrieve_organization_accounts.py

AWS Account details of the member accounts in the organization are
required for services like AWS Security Hub and Amazon GuardDuty.

This helper script will allow you to retrieve all the member account
details of the accounts in the organization as part of the CodeBuild
step. The member account details will be written to a JSON file on the
path as specified during execution.

For example, to get the account details required for AWS Security Hub
to send the invites correctly, you would need to execute the script
with the arguments to fetch the details as shown in the last example.

This will write the JSON file directly inside the code base of the
custom resource. Such that the lambda function can read and act based
on that data from inside a target account. Without requiring special
permissions to be added to target accounts to traverse the AWS
Organization.

Usage:
    retrieve_organization_accounts.py [-v | --verbose] [-h | --help]
                [-r <role-name>] [-o <output-file-path>] [-s <session-name>]
                [--session-ttl <seconds>] [-f <field>]...

Options:
    -f <field>, --field <field>
                Add a specific field that is available in the organization
                member account details. Available options include 'Id', 'Arn',
                'Email', 'Name', 'Status', 'JoinedMethod', 'JoinedTimestamp'.
                You can specify multiple by adding them one after another.
                All other details that would otherwise be returned by the
                AWS Organizations: ListAccounts API call will be ignored
                [default: Id Email Name].

    -h, --help  Show help info related to generic or command
                execution.

    -o <output-file-path>, --output-file <output-file-path>
                The output file path to use to output the retrieved
                data to in JSON format. Define a file path or set to - to
                output to stdout [default: -].

    -r <role-name>, --role-name <role-name>
                The name of the role to assume into to get read access
                to list and describe the member accounts in the
                organization [default: OrganizationAccountAccessRole-readonly].

    -s <session-name>, --session-name <session-name>
                The session name to use when assuming into the billing account
                role [default: retrieve_organization_accounts].

    --session-ttl <in-seconds>
                The STS TTL in seconds [default: 900].

    -v, --verbose
                Show verbose logging information.

Example:
    retrieve_organization_accounts.py -v -o src/lambda/accounts.json

    retrieve_organization_accounts.py -v -f Id -f Email -o src/lambda/dat.json
"""

import sys
import logging
import json

import boto3
from botocore.exceptions import ClientError

from docopt import docopt


# Configure logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def main():
    """
    AWS Account details of the member accounts in the organization are
    required for services like AWS Security Hub and Amazon GuardDuty.

    This helper script will allow you to retrieve all the member account
    details of the accounts in the organization as part of the CodeBuild
    step. The member account details will be written to a JSON file on the
    path as specified during execution.

    For example, to get the account details required for Security Hub to
    send the invites correctly, you would need to execute the script with
    the following arguments to fetch the details:

    ```bash
      python adf-build/helpers/retrieve_organization_accounts.py -v \
          -o src/custom_resource/invite_members/member_accounts.json \
          -f Id \
          -f Email
    ```

    This will write the JSON file directly inside the code base of the
    `invite_members` custom resource. Such that the lambda function can
    read and act based on that data from inside a target account without
    requiring special permissions to be added to target accounts to traverse
    the AWS Organization.

    The two options defined using the `-f` argument, specify that we are
    interested in the `Id` and the `Email` of the member accounts.
    All other details that would otherwise be returned by the
    [Organizations: ListAccounts](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/organizations.html#Organizations.Client.list_accounts)
    API will be ignored.

    ---

    This main function will parse the arguments using docopt to determine what
    options are relevant. See command options listed at the top of this file
    or run the script with `--help` to get the list of options instead.

    Based on the input, it will traverse the accounts linked to the
    AWS Organization and store the details as requested in a JSON file.

    Returns:
        int: Exit code 0 when all went well.
    """
    options = docopt(__doc__)

    # In case the user asked for verbose logging, increase
    # the log level to debug.
    if options['--verbose'] > 0:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug(
        "Received options: %s",
        options,
    )

    billing_account_id = _get_billing_account_id()
    member_accounts = _get_member_accounts(
        billing_account_id=billing_account_id,
        options=options,
    )
    _flush_out(accounts=member_accounts, options=options)

    return 0


def _get_partition(region_name: str) -> str:
    """Given the region, this function will return the appropriate partition.

    :param region_name: The name of the region (us-east-1, us-gov-west-1)
    :return: Returns the partition name as a string.
    """

    if region_name.startswith('us-gov'):
        return 'aws-us-gov'

    return 'aws'


def _get_billing_account_id():
    """
    Retrieve the Billing/Root AWS Account Id of the organization.

    Returns:
        str: The AWS Account Id as a string.
    """
    org_client = boto3.client('organizations')
    response = org_client.describe_organization()
    return response['Organization']['MasterAccountId']


def _get_member_accounts(billing_account_id, options):
    """
    Retrieve the member accounts of the AWS Organization as requested.

    Args:
        billing_account_id (str): The Billing/Root AWS Account Id of the
            organization.

        options (dict): The options stored as a dictionary. These include all
            argument options as passed when executing the script.

    Returns:
        list(dict)): The list of account details as requested.
    """
    assumed_credentials = _request_sts_credentials(
        billing_account_id=billing_account_id,
        options=options,
    )
    billing_account_session = boto3.Session(
        aws_access_key_id=assumed_credentials['AccessKeyId'],
        aws_secret_access_key=assumed_credentials['SecretAccessKey'],
        aws_session_token=assumed_credentials['SessionToken'],
    )
    org_client = billing_account_session.client('organizations')
    list_accounts_paginator = org_client.get_paginator('list_accounts')
    accounts = []
    for page in list_accounts_paginator.paginate():
        accounts.extend(
            page['Accounts']
        )

    # Remove any account that is not actively part of this organization yet.
    only_active_accounts = filter(lambda a: a['Status'] == 'ACTIVE', accounts)

    # Only return the key: value pairs that are defined in the --field option.
    only_certain_fields_of_active = list(map(
        lambda a: {k: v for k, v in a.items() if k in options['--field']},
        only_active_accounts
    ))
    return only_certain_fields_of_active


def _flush_out(accounts, options):
    """
    Flush the account details to the specified output target. When the output
    file option equals `-` it will output to the INFO logger. Otherwise, it
    will write to the specified target file as requested.

    Args:
        accounts (list(dict)): The account details to flush to the file/logs.
        options (dict): The options which host where to write the account
            details to among other flags.
    """
    json_accounts = json.dumps(accounts, indent=2, default=str)

    if options['--output-file'] == '-':
        LOGGER.info(
            "Accounts JSON: %s",
            json_accounts,
        )
        return

    with open(options['--output-file'], mode='w', encoding='utf-8') as output_file:
        output_file.write(json_accounts)


def _request_sts_credentials(billing_account_id, options):
    """
    Request STS Credentials to get access to the billing account.
    With the assumed role, this script will be able to traverse over the
    member accounts in the AWS Organization.

    Args:
        billing_account_id (str): The Billing/Root AWS Account Id of the
            organization.

        options (dict): The options stored as a dictionary. These include all
            argument options as passed when executing the script.

    Returns:
        dict: The credentials stored in a dictionary. This will host the
        `AccessKeyId`, `SecretAccessKey`, and `SessionToken` attributes
        required to use the STS role.
    """
    try:

        # Setup Session
        session = boto3.session.Session()
        region_name = session.region_name
        partition = _get_partition(region_name)
        sts_client = session.client('sts')

        role_name = options['--role-name']
        role_arn = f'arn:{partition}:iam::{billing_account_id}:role/{role_name}'
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=options['--session-name'],
            DurationSeconds=int(options['--session-ttl']),
        )
        return response['Credentials']
    except ClientError as client_error:
        LOGGER.error("Failed to assume into role")
        LOGGER.exception(client_error)
        raise


if __name__ == '__main__':
    sys.exit(main())
