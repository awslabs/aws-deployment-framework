# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for working with the Deployment Map (yml) file.
"""

import os
import sys
import json
import yaml

from schema import SchemaError
from schema_validation import SchemaValidation
from errors import InvalidDeploymentMapError
from logger import configure_logger

LOGGER = configure_logger(__name__)

class DeploymentMap:
    def __init__(
            self,
            parameter_store,
            s3,
            pipeline_name_prefix,
            map_path=None
    ):
        self.map_path = map_path or 'deployment_map.yml'
        self.map_dir_path = map_path or 'deployment_maps'
        self.parameter_store = parameter_store
        self.s3 = s3
        self._get_all()
        self.pipeline_name_prefix = pipeline_name_prefix
        self.account_ou_names = {}

    def update_deployment_parameters(self, pipeline):
        for target in pipeline.template_dictionary['targets']:
            for _t in target:
                if _t.get('target'): # Allows target to be interchangeable with path
                    _t['path'] = _t.pop('target')
                if _t.get('path'):
                    self.account_ou_names.update(
                        {item['name']: item['path'] for item in target if item['name'] != 'approval'}
                    )
        with open('{0}.json'.format(pipeline.name), 'w') as outfile:
            json.dump(self.account_ou_names, outfile)
        self.s3.put_object(
            "adf-parameters/deployment/{0}/account_ous.json".format(
                pipeline.name
            ),
            '{0}.json'.format(pipeline.name)
        )
        if pipeline.notification_endpoint:
            self.parameter_store.put_parameter(
                "/notification_endpoint/{0}".format(
                    pipeline.name
                ),
                str(pipeline.notification_endpoint)
            )

    def _read(self, file_path=None):
        if file_path is None:
            file_path = self.map_path
        try:
            LOGGER.info('Loading deployment_map file %s', file_path)
            with open(file_path, 'r') as stream:
                _input = yaml.load(stream, Loader=yaml.FullLoader)
                return SchemaValidation(_input).validated
        except FileNotFoundError:
            LOGGER.info('No default map file found at %s, continuing', file_path)
            return {}
        except SchemaError as err:
            LOGGER.error(err.code)
            sys.exit(1)

    def determine_extend_map(self, deployment_map):
        if deployment_map.get('pipelines'):
            self.map_contents['pipelines'].extend(deployment_map['pipelines'])

    def _get_all(self):
        self.map_contents = {}
        self.map_contents['pipelines'] = []
        if os.path.isdir(self.map_dir_path):
            for file in os.listdir(self.map_dir_path):
                if file.endswith(".yml") and file != 'example-deployment_map.yml':
                    self.determine_extend_map(
                        self._read('{0}/{1}'.format(self.map_dir_path, file))
                    )
        self.determine_extend_map(
            self._read() # Calling with default no args to get deployment_map.yml in root if it exists
        )
        if not self.map_contents['pipelines']:
            LOGGER.error(
                "No Deployment Map files found, create a deployment_map.yml file in the root of the repository to create pipelines. "
                "You can create additional deployment maps if required in a folder named deployment_maps with any name (ending in .yml)"
            )
            raise InvalidDeploymentMapError("No Deployment Map files found..") from None
