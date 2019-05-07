# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the parameters for cloudformation stacks based on
   param files in the params folder
"""

import json
import os
import ast
import boto3

from resolver import Resolver
from logger import configure_logger
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
PROJECT_NAME = os.environ.get('PROJECT_NAME')


class Parameters:
    def __init__(self, build_name, parameter_store, directory=None):
        self.cwd = directory or os.getcwd()
        self._create_params_folder()
        self.global_path = "params/global.json"
        self.parameter_store = parameter_store
        self.build_name = build_name
        self.account_ous = ast.literal_eval(
            parameter_store.fetch_parameter(
                "/deployment/{0}/account_ous".format(self.build_name)
            )
        )
        self.regions = ast.literal_eval(
            parameter_store.fetch_parameter(
                "/deployment/{0}/regions".format(self.build_name)
            )
        )

    def _create_params_folder(self):
        try:
            return os.mkdir('{0}/params'.format(self.cwd))
        except FileExistsError:
            return None

    def create_parameter_files(self):
        global_params = self._parse(self.global_path)
        for acc, ou in self.account_ous.items():
            for region in self.regions:
                for params in ["{0}_{1}.json".format(acc, region)]:
                    compare_params = self._compare(
                        self._parse("{0}/params/{1}.json".format(self.cwd, acc)),
                        self._parse("{0}/params/{1}".format(self.cwd, params))
                    )

                    if not str(ou).isnumeric():
                        # Compare account_region final to ou_region
                        compare_params = self._compare(
                            self._parse("{0}/params/{1}_{2}.json".format(self.cwd, ou, region)),
                            compare_params
                        )
                        # Compare account_region final to ou
                        compare_params = self._compare(
                            self._parse("{0}/params/{1}.json".format(self.cwd, ou)),
                            compare_params
                        )
                    # Compare account_region final to deployment_account_region
                    compare_params = self._compare(
                        self._parse("{0}/params/global_{1}.json".format(self.cwd, region)),
                        compare_params
                    )
                    # Compare account_region final to global
                    compare_params = self._compare(
                        global_params,
                        compare_params
                    )

                    if compare_params is not None:
                        self._update_params(compare_params, params)

    def _parse(self, filename):  # pylint: disable=R0201
        """
        Attempt to parse the parameters file and return he default
        CloudFormation parameter base object if not found. Returning
        Base CloudFormation Parameters here since if the user was using
        Any other type (SC, ECS) they would require a parameter file (global.json)
        and thus this would not fail.
        """
        try:
            with open(filename) as file:
                return json.load(file)
        except FileNotFoundError:
            return {'Parameters': {}, 'Tags': {}}

    def _update_params(self, new_params, filename):
        """
        Responsible for updating the parameters within the files themself
        """
        with open("{0}/params/{1}".format(self.cwd, filename), 'w') as outfile:
            json.dump(new_params, outfile)

    def _cfn_param_updater(self, param, comparison_parameters, stage_parameters):
        """
        Generic CFN Updater method
        """
        resolver = Resolver(self.parameter_store, stage_parameters, comparison_parameters)

        for key, value in comparison_parameters[param].items():
            if str(value).startswith('resolve:'):
                if resolver.fetch_parameter_store_value(value, key, param):
                    continue
            if str(value).startswith('import:'):
                if resolver.fetch_stack_output(value, key, param):
                    continue
            resolver.update_cfn(key, param)

        for key, value in stage_parameters[param].items():
            if str(value).startswith('resolve:'):
                if resolver.fetch_parameter_store_value(value, key, param):
                    continue
            if str(value).startswith('import:'):
                if resolver.fetch_stack_output(value, key, param):
                    continue

        return resolver.__dict__.get('stage_parameters')

    def _compare_cfn(self, comparison_parameters, stage_parameters):
        """
        Compares parameter files used for the CloudFormation deployment type
        """
        if comparison_parameters.get('Parameters'):
            stage_parameters = self._cfn_param_updater(
                'Parameters', comparison_parameters, stage_parameters
            )
        if comparison_parameters.get('Tags'):
            stage_parameters = self._cfn_param_updater(
                'Tags', comparison_parameters, stage_parameters
            )

        return stage_parameters

    def _sc_param_updater(self, comparison_parameters, stage_parameters):
        """
        Compares parameter files used for the Service Catalog deployment type
        """
        resolver = Resolver(self.parameter_store, stage_parameters, comparison_parameters)

        for key, value in comparison_parameters.items():
            if str(value).startswith('resolve:'):
                if resolver.fetch_parameter_store_value(value, key):
                    continue
            if str(value).startswith('import:'):
                if resolver.fetch_stack_output(value, key):
                    continue
            resolver.update_sc(key)

        for key, value in stage_parameters.items():
            if str(value).startswith('resolve:'):
                if resolver.fetch_parameter_store_value(value, key):
                    continue
            if str(value).startswith('import:'):
                if resolver.fetch_stack_output(value, key):
                    continue

        return resolver.__dict__.get('stage_parameters')

    def _compare(self, comparison_parameters, stage_parameters):
        """
        Determine the type of parameter file that should be compared
        (currently only SC/CFN)
        """
        if comparison_parameters.get('Parameters') or comparison_parameters.get('Tags'):
            return self._compare_cfn(comparison_parameters, stage_parameters)
        return self._sc_param_updater(comparison_parameters, stage_parameters)


def main():
    parameters = Parameters(
        PROJECT_NAME,
        ParameterStore(
            DEPLOYMENT_ACCOUNT_REGION,
            boto3
        )
    )
    parameters.create_parameter_files()



if __name__ == '__main__':
    main()
