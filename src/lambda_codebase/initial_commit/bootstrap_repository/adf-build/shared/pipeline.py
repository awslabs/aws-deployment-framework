# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
from jinja2 import Environment, FileSystemLoader

DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')

class Pipeline:
    def __init__(self, pipeline):
        self.name = pipeline.get('name')
        self.parameters = pipeline.get('params', [])
        self.template_dictionary = {"targets": []}
        self.notification_endpoint = self._extract_notification_endpoint()
        self.stage_regions = []
        self.top_level_regions = pipeline.get('regions', [])
        self.deployment_role = pipeline.get('deployment_role', None)
        self.pipeline_type = pipeline.get('type', None)
        self.action = pipeline.get('action', '').upper()
        self.completion_trigger = pipeline.get('completion_trigger', {})
        self.contains_transform = pipeline.get('contains_transform', '')
        if not isinstance(self.completion_trigger.get('pipelines', []), list):
            self.completion_trigger['pipelines'] = [self.completion_trigger['pipelines']]
        if not isinstance(self.top_level_regions, list):
            self.top_level_regions = [self.top_level_regions]


    def _extract_notification_endpoint(self):
        for parameter in self.parameters:
            endpoint = parameter.get('NotificationEndpoint')
            if endpoint:
                return endpoint
        return None


    def generate_parameters(self):
        params = []
        # ProjectName should be a hidden param and passed in directly from the
        # name of the "pipeline"
        params.append({
            'ParameterKey': str('ProjectName'),
            'ParameterValue': self.name,
        })
        for param in self.parameters:
            for key, value in param.items():
                params.append({
                    'ParameterKey': str(key),
                    'ParameterValue': str(value),
                })
        return params


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

    def generate(self):
        env = Environment(loader=FileSystemLoader('pipeline_types'))
        template = env.get_template('./{0}.yml.j2'.format(self.pipeline_type))
        output_template = template.render(
            environments=self.template_dictionary,
            name=self.name,
            notification_endpoint=self.notification_endpoint,
            top_level_regions=sorted(self.flatten_list(list(set(self.top_level_regions)))),
            regions=sorted(list(set(self.flatten_list(self.stage_regions)))),
            deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
            deployment_role=self.deployment_role,
            action=self.action,
            contains_transform=self.contains_transform,
            completion_trigger=self.completion_trigger
        )
        self._create_pipelines_folder()
        self._write_output(output_template)
