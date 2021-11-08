# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Main
"""

#!/usr/bin/env python3

import os
from concurrent.futures import ThreadPoolExecutor
import boto3
import tenacity
from organizations import Organizations
from logger import configure_logger
from parameter_store import ParameterStore
from partition import get_partition
from sts import STS
from src import read_config_files, delete_default_vpc, Support

REGION_DEFAULT = os.getenv('AWS_REGION')

LOGGER = configure_logger(__name__)
ACCOUNTS_FOLDER = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'adf-accounts'))


def main():
    accounts = read_config_files(ACCOUNTS_FOLDER)
    if not bool(accounts):
        LOGGER.info(
            f"Found {len(accounts)} account(s) in configuration file(s). "
            f"Account provisioning will not continue."
        )
        return
    LOGGER.info(f"Found {len(accounts)} account(s) in configuration file(s).")
    organizations = Organizations(boto3)
    support = Support(boto3)
    all_accounts = organizations.get_accounts()
    parameter_store = ParameterStore(
        os.environ.get('AWS_REGION', 'us-east-1'),
        boto3
    )
    adf_role_name = parameter_store.fetch_parameter(
        'cross_account_access_role')
    for account in accounts:
        try:
            account_id = next(
                acc["Id"] for acc in all_accounts if acc["Name"] == account.full_name)
        except StopIteration:  # If the account does not exist yet..
            account_id = None
        create_or_update_account(
            organizations, support, account, adf_role_name, account_id)


def create_or_update_account(org_session, support_session, account, adf_role_name, account_id=None):
    """Creates or updates a single AWS account.
    :param org_session: Instance of Organization class
    :param account: Instance of Account class
    """
    if not account_id:
        LOGGER.info(f'Creating new account {account.full_name}')
        account_id = org_session.create_account(account, adf_role_name)
        # This only runs on account creation at the moment.
        support_session.set_support_level_for_account(account, account_id)

    sts = STS()
    partition = get_partition(REGION_DEFAULT)
    role = sts.assume_cross_account_role(
        f'arn:{partition}:iam::{account_id}:role/{adf_role_name}',
        'adf_account_provisioning'
    )

    LOGGER.info(
        f'Ensuring account {account_id} (alias {account.alias}) is in '
        f'OU {account.ou_path}'
    )
    org_session.move_account(account_id, account.ou_path)
    if account.delete_default_vpc:
        ec2_client = role.client('ec2')
        all_regions = get_all_regions(ec2_client)
        args = (
            (account_id, region, role)
            for region in all_regions
        )
        with ThreadPoolExecutor(max_workers=10) as executor:
            for _ in executor.map(lambda f: schedule_delete_default_vpc(*f), args):
                pass

    if account.alias:
        LOGGER.info(f'Ensuring account alias for {account_id} of {account.alias}')
        org_session.create_account_alias(account.alias, role)

    if account.tags:
        LOGGER.info(
            f'Ensuring tags exist for account {account_id}: {account.tags}')
        org_session.create_account_tags(account_id, account.tags)


@tenacity.retry(
    stop=tenacity.stop_after_attempt(9),
    wait=tenacity.wait_random_exponential(),
)
def get_all_regions(ec2_client):
    try:
        all_regions = [
            region['RegionName']
            for region in ec2_client.describe_regions(
                AllRegions=False,
                Filters=[
                    {
                        'Name': 'opt-in-status',
                        'Values': [
                            'opt-in-not-required',
                        ]
                    }
                ]
            )['Regions']
        ]
        LOGGER.info(f'Regions are: {all_regions}')
        return all_regions
    except Exception as ce:
        LOGGER.info('Failed to describe regions: %s, retrying...', ce)
        raise


def schedule_delete_default_vpc(account_id, region, role):
    """Schedule a delete_default_vpc on a thread
    :param account_id: The account ID to remove the VPC from
    :param org_session: The Organization class instance
    :param region: The name of the region the VPC is resided
    """
    ec2_client = role.client('ec2', region_name=region)
    delete_default_vpc(ec2_client, account_id, region, role)


if __name__ == '__main__':
    main()
