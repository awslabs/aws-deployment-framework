# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os

DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]

class Pipeline:
    def __init__(self, pipeline):
        self.name = pipeline.get('name')
        self.default_providers = pipeline.get('default_providers', {})
        self.parameters = pipeline.get('params', {})
        self.input = {}
        self.template_dictionary = {"targets": []}
        self.notification_endpoint = self.parameters.get('notification_endpoint', None)
        self.stage_regions = []
        self.top_level_regions = pipeline.get('regions', [])
        self.completion_trigger = pipeline.get('completion_trigger', {})
        self.tags = pipeline.get('tags', {})
        self.schedule = self.parameters.get('schedule', {})
        if not isinstance(self.completion_trigger.get('pipelines', []), list):
            self.completion_trigger['pipelines'] = [self.completion_trigger['pipelines']]
        if not isinstance(self.top_level_regions, list):
            self.top_level_regions = [self.top_level_regions]

    @staticmethod
    def flatten_list(input_list):
        result = []
        for item in input_list:
            if isinstance(item, list):
                result.extend(Pipeline.flatten_list(item))
            else:
                result.append(item)
        return sorted(result)

    def _create_pipelines_folder(self):
        try:
            return os.makedirs(f"pipelines/{self.name}")
        except FileExistsError:
            return None

    def _write_output(self, output_template):
        output_path = f"pipelines/{self.name}/global.yml"
        with open(output_path, mode='w', encoding='utf-8') as file_handler:
            file_handler.write(output_template)

    def _input_type_validation(self, params): #pylint: disable=R0201
        if not params.get('default_providers', {}).get('build', {}):
            params['default_providers']['build'] = {}
            params['default_providers']['build']['provider'] = 'codebuild'
        if not params.get('default_providers', {}).get('deploy', {}):
            params['default_providers']['deploy'] = {}
            params['default_providers']['deploy']['provider'] = 'cloudformation'
        return params

    def generate_input(self):
        self.input = self._input_type_validation({
            "environments": self.template_dictionary,
            "name": self.name,
            "params": self.parameters,
            "tags": self.tags,
            "default_providers": self.default_providers,
            "top_level_regions": sorted(self.flatten_list(list(set(self.top_level_regions)))),
            "regions": sorted(list(set(self.flatten_list(self.stage_regions)))),
            "deployment_account_region": DEPLOYMENT_ACCOUNT_REGION,
            "completion_trigger": self.completion_trigger,
            "schedule": self.schedule
        })
