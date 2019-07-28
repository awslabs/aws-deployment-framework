# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""S3 module used throughout the ADF
"""

import boto3

from logger import configure_logger


LOGGER = configure_logger(__name__)


class S3:
    """Class used for modeling S3
    """

    def __init__(self, region, bucket):
        self.region = region
        self.client = boto3.client('s3', region_name=region)
        self.resource = boto3.resource('s3', region_name=region)
        self.bucket = bucket

    def build_pathing_style(self, style, key):
        if style == 'path':
            if self.region == 'us-east-1':
                return "https://s3.amazonaws.com/{bucket}/{key}".format(
                    bucket=self.bucket,
                    key=key
                )
            return "https://s3-{region}.amazonaws.com/{bucket}/{key}".format(
                region=self.region,
                bucket=self.bucket,
                key=key
            )
        if style == 'virtual-hosted':
            if self.region == 'us-east-1':
                return "http://{bucket}.s3.amazonaws.com/{key}".format(
                    bucket=self.bucket,
                    key=key
                )
            return "http://{bucket}.s3-{region}.amazonaws.com/{key}".format(
                region=self.region,
                bucket=self.bucket,
                key=key
            )
        raise Exception("Unknown upload style syntax, path or virtual-hosted must be specified.")


    def put_object(self, key, file_path, style="path"):
        """
        Put the object into S3 and return the S3 URL of the object
        """
        self.resource.Object(self.bucket, key).put(Body=open(file_path, 'rb'))
        return self.build_pathing_style(style, key)

    def read_object(self, key):
        s3_object = self.resource.Object(self.bucket, key)
        return s3_object.get()['Body'].read().decode('utf-8')

    def fetch_s3_url(self, key):
        """Recursively search for an object in S3 and return its URL
        """

        try:
            s3_object = self.resource.Object(self.bucket, key)
            s3_object.get()
            LOGGER.debug('Found Template at: %s', s3_object.key)
            if self.region == 'us-east-1':
                return "https://s3.amazonaws.com/{bucket}/{key}".format(
                    bucket=self.bucket,
                    key=key
                )
            return "https://s3-{region}.amazonaws.com/{bucket}/{key}".format(
                region=self.region,
                bucket=self.bucket,
                key=key
            )
        except self.client.exceptions.NoSuchKey:
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
            return self.fetch_s3_url(next_level_up_key)
