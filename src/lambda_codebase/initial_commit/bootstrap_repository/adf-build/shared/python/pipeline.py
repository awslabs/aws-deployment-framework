# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
from copy import deepcopy
from list_utils import flatten_to_unique_sorted

DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]


class Pipeline:
    def __init__(self, pipeline):
        self.name = pipeline.get('name')
        self.default_providers = self._set_default_provider_defaults(
            pipeline.get('default_providers'),
        )
        self.parameters = pipeline.get('params', {})
        self.template_dictionary = {"targets": []}
        self.notification_endpoint = self.parameters.get(
            'notification_endpoint',
        )
        self.stage_regions = []
        self.top_level_regions = pipeline.get('regions', [])
        self.completion_trigger = pipeline.get('completion_trigger', {})
        self.tags = pipeline.get('tags', {})
        self.schedule = self.parameters.get('schedule', {})
        if not isinstance(self.completion_trigger.get('pipelines', []), list):
            self.completion_trigger['pipelines'] = [
                self.completion_trigger['pipelines'],
            ]
        if not isinstance(self.top_level_regions, list):
            self.top_level_regions = [self.top_level_regions]

    def _create_pipelines_folder(self):
        try:
            return os.makedirs(f"pipelines/{self.name}")
        except FileExistsError:
            return None

    def _write_output(self, output_template):
        output_path = f"pipelines/{self.name}/global.yml"
        with open(output_path, mode='w', encoding='utf-8') as file_handler:
            file_handler.write(output_template)

    def get_all_regions(self):
        """
        Get all the regions specified for this pipeline.
        This includes the regions that are defined at the top level of the
        pipeline, being the `$.regions`. As well as the `$.targets.[].regions`.

        Returns:
            list(str): The list of regions that this pipeline has configured.
        """
        return flatten_to_unique_sorted(
            [
                self.top_level_regions or [],
                self.stage_regions,
            ],
        )

    @staticmethod
    def _set_default_provider_defaults(default_providers):
        providers = default_providers or {}
        return {
            'source': {
                'provider': 'codecommit',
                **providers.get('source', {}),
            },
            'build': {
                'provider': 'codebuild',
                **providers.get('build', {}),
            },
            'deploy': {
                'provider': 'cloudformation',
                **providers.get('deploy', {}),
            },
        }

    def merge_in_deploy_defaults(self, deploy_target_config):
        """
        Pass the step or target deployment configuration here to
        get the default configuration applied if the provider or its
        properties are not configured.

        Args:
            deploy_target_config (dict): The target deployment configuration
                dict holding the provider type attribute and its properties.

        Returns:
            dict: The updated target deployment configuration, including the
                defaults where those were overwritten yet.
        """
        new_config = deepcopy(deploy_target_config)
        default_deploy = self.default_providers.get('deploy')
        if not new_config.get('provider'):
            new_config['provider'] = (
                default_deploy.get('provider')
            )
        new_config['properties'] = {
            **default_deploy.get('properties', {}),
            **new_config.get('properties', {}),
        }
        if new_config.get('regions') is None:
            new_config['regions'] = (
                self.top_level_regions
                or [DEPLOYMENT_ACCOUNT_REGION]
            )
        return new_config

    def generate_input(self):
        """
        Generate the pipeline input data.

        Returns:
            dict: The pipeline input data.
        """
        pipeline_input = {
            "environments": self.template_dictionary,
            "name": self.name,
            "params": self.parameters,
            "tags": self.tags,
            "default_providers": self.default_providers,
            "regions": self.get_all_regions(),
            "deployment_account_region": DEPLOYMENT_ACCOUNT_REGION,
            "completion_trigger": self.completion_trigger,
            "schedule": self.schedule,
        }
        return pipeline_input
