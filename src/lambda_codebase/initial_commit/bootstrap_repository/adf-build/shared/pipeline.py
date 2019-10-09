# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        self.type = pipeline.get('type', {})
        self.parameters = pipeline.get('params', {})
        self.input = {}
        self.template_dictionary = {"targets": []}
        self.notification_endpoint = self.parameters.get('notification_endpoint', None)
        self.stage_regions = []
        self.top_level_regions = pipeline.get('regions', [])
        self.completion_trigger = pipeline.get('completion_trigger', {})
        self.schedule = self.parameters.get('schedule', {})
        self.contains_transform = pipeline.get('contains_transform', '')
        if not isinstance(self.completion_trigger.get('pipelines', []), list):
            self.completion_trigger['pipelines'] = [self.completion_trigger['pipelines']]
        if not isinstance(self.top_level_regions, list):
            self.top_level_regions = [self.top_level_regions]

    @staticmethod
    def flatten_list(input_list):
        result = list()
        for item in input_list:
            if isinstance(item, list):
                result.extend(Pipeline.flatten_list(item))
            else:
                result.append(item)
        return sorted(result)

    def _create_pipelines_folder(self):
        try:
            return os.makedirs("pipelines/{0}".format(self.name))
        except FileExistsError:
            return None

    def _write_output(self, output_template):
        output_path = "pipelines/{0}/global.yml".format(self.name)
        with open(output_path, 'w') as file_handler:
            file_handler.write(output_template)

    def _input_type_validation(self, params): #pylint: disable=R0201
        if not params.get('type', {}):
            params['type'] = {}
        if params.get('type', {}).get('source', {}).get('name') == 'codecommit':
            if not params.get('type', {}).get('source', {}).get('account_id'):
                raise Exception('Invalid source configuration, you must specify a source name and account_id property')
        if not params.get('type', {}).get('source', {}):
            params['type']['source']['name'] = 'codecommit'
        if not params.get('type', {}).get('build', {}):
            params['type']['build'] = {}
            params['type']['build']['name'] = 'codebuild'
        if not params.get('type', {}).get('build', {}).get('enabled'):
            params['type']['build']['name'] = 'codebuild'
        if not params.get('type', {}).get('deploy', {}):
            params['type']['deploy'] = {}
            params['type']['deploy']['name'] = 'cloudformation'
        return params

    def generate_input(self):
        self.input = self._input_type_validation({
            "environments": self.template_dictionary,
            "name": self.name,
            "type": self.type,
            "notification_endpoint": self.notification_endpoint,
            "top_level_regions": sorted(self.flatten_list(list(set(self.top_level_regions)))),
            "regions": sorted(list(set(self.flatten_list(self.stage_regions)))),
            "deployment_account_region": DEPLOYMENT_ACCOUNT_REGION,
            "contains_transform": self.contains_transform,
            "completion_trigger": self.completion_trigger,
            "schedule": self.schedule
        })
