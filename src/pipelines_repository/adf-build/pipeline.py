# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
from jinja2 import Environment, FileSystemLoader

DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Pipeline:
    def __init__(self, pipeline):
        self.name = pipeline.get('name')
        self.parameters = pipeline.get('params', [])
        self.template_dictionary = {"targets": []}
        self.stage_regions = []
        self.top_level_regions = pipeline.get('regions', [])
        self.pipeline_type = pipeline.get('type', None)
        self.file_path = "{0}/{1}/{2}".format(TARGET_DIR,
                                              'pipelines', self.name)

        if not isinstance(self.top_level_regions, list):
            self.top_level_regions = [self.top_level_regions]

    def generate_parameters(self):
        try:
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
        except BaseException:
            return []

    @staticmethod
    def flatten_list(k):
        result = list()
        for i in k:
            if isinstance(i, list):
                result.extend(Pipeline.flatten_list(i))
            else:
                result.append(i)
        return result

    def _create_pipelines_folder(self):
        try:
            return os.makedirs("pipelines/{0}".format(self.name))
        except FileExistsError:
            return None

    def generate(self):
        env = Environment(loader=FileSystemLoader('pipeline_types'))
        template = env.get_template('./{0}.yml.j2'.format(self.pipeline_type))
        output_template = template.render(
            environments=self.template_dictionary,
            name=self.name,
            top_level_regions=self.flatten_list(list(set(self.top_level_regions))),
            regions=list(set(self.flatten_list(self.stage_regions))),
            deployment_account_region=DEPLOYMENT_ACCOUNT_REGION
        )

        self._create_pipelines_folder()

        output_path = "pipelines/{0}/global.yml".format(self.name)
        with open(output_path, 'w') as file_handler:
            file_handler.write(output_template)
