# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""S3 module used throughout the ADF
"""

from botocore.exceptions import ClientError
from logger import configure_logger


LOGGER = configure_logger(__name__)


class S3:
    """Class used for modeling S3
    """

    def __init__(self, region, role, bucket):
        self.resource = role.resource('s3', region_name=region)
        self.client = role.client('s3', region_name=region)
        self.bucket = bucket
        self.policy = None

    def s3_stream_object(self, key):
        """Stream an S3 Objects data into utf-8 to be consumed by CloudFormation
        """

        try:
            s3_object = self.resource.Object(self.bucket, key)
            template = s3_object.get()['Body'].read().decode('utf-8')
            LOGGER.info('Found Template at: %s', key)
            return template
        except ClientError:
            # Split the path to remove the last key entry from the string
            key_level_up = key.split('/')

            # Return None here if nothing could be found from recursive
            # searching
            if len(key_level_up) == 1:
                LOGGER.debug(
                    'Nothing could be found for %s when traversing the bucket', key)
                return []

            LOGGER.debug(
                'Unable to find the specified Key: %s - looking one level up', key)
            # remove the key name in which we did not find the file we wanted this attempt
            # (-1 will be json/yml file, -2 will be the key prefix) which we want to leave
            del key_level_up[-2]

            # Join it back together, and recursive call the function with the
            # new trimmed key until a template/params is found
            next_level_up_key = '/'.join(key_level_up)
            return self.s3_stream_object(next_level_up_key)

    def _get_bucket_policy(self):
        return self.policy

    def _set_bucket_policy(self, policy):
        self.policy = policy

    def _put_bucket_policy(self):
        return self.client.put_bucket_policy(
            Bucket=self.bucket,
            Policy=self._get_bucket_policy()
        )

    def _fetch_bucket_policy(self):
        return self.client.get_bucket_policy(
            Bucket=self.bucket
        ).get('Policy')

    @staticmethod
    def _sanitize_policy(policy):
        policy_to_validate = policy.get(
            "Statement", [])[0].get("Principal").get('AWS')

        sanitized = list(filter(
            lambda p: p.startswith('arn'),
            policy_to_validate
        ))

        policy["Statement"][0]["Principal"]["AWS"] = sanitized

        return policy
