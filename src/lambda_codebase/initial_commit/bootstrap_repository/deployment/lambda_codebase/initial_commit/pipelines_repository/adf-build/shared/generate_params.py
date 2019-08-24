# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the parameters for cloudformation stacks based on
   param files in the params folder
"""

import json
import secrets
import string # pylint: disable=deprecated-module # https://www.logilab.org/ticket/2481
import os
import ast
import yaml
import boto3

from resolver import Resolver
from logger import configure_logger
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]

class Parameters:
    def __init__(self, build_name, parameter_store, directory=None):
        self.cwd = directory or os.getcwd()
        self._create_params_folder()
        self.global_path = "params/global"
        self.parameter_store = parameter_store
        self.build_name = build_name
        self.file_name = "".join(
            secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6)
        )
        [self.account_ous, self.regions] = self._fetch_initial_parameter()

    def _fetch_initial_parameter(self):
        return [
            ast.literal_eval(
                self.parameter_store.fetch_parameter(
                    "/deployment/{0}/account_ous".format(self.build_name)
                )
            ),
            ast.literal_eval(
                self.parameter_store.fetch_parameter(
                    "/deployment/{0}/regions".format(self.build_name)
                )
            )
        ]

    def _create_params_folder(self):
        try:
            return os.mkdir('{0}/params'.format(self.cwd))
        except FileExistsError:
            return None

    @staticmethod
    def _is_account_id(value):
        return str(value).isnumeric()

    def create_parameter_files(self):
        for account, ou in self.account_ous.items():
            for region in self.regions:
                compare_params = self._param_updater(
                    Parameters._parse("{0}/params/{1}".format(self.cwd, account)),
                    Parameters._parse("{0}/params/{1}".format(self.cwd, "{0}_{1}".format(account, region)))
                )
                if not Parameters._is_account_id(ou):
                    # Compare account_region final to ou_region
                    compare_params = self._param_updater(
                        Parameters._parse("{0}/params/{1}_{2}".format(self.cwd, ou, region)),
                        compare_params
                    )
                    # Compare account_region final to ou
                    compare_params = self._param_updater(
                        Parameters._parse("{0}/params/{1}".format(self.cwd, ou)),
                        compare_params
                    )
                # Compare account_region final to deployment_account_region
                compare_params = self._param_updater(
                    Parameters._parse("{0}/params/global_{1}".format(self.cwd, region)),
                    compare_params
                )
                # Compare account_region final to global
                compare_params = self._param_updater(
                    Parameters._parse(self.global_path),
                    compare_params
                )
                if compare_params is not None:
                    self._update_params(compare_params, "{0}_{1}".format(account, region))

    @staticmethod
    def _parse(filename):
        """
        Attempt to parse the parameters file and return he default
        CloudFormation parameter base object if not found. Returning
        Base CloudFormation Parameters here since if the user was using
        Any other type (SC, ECS) they would require a parameter file (global.json)
        and thus this would not fail.
        """
        try:
            with open("{0}.json".format(filename)) as file:
                return json.load(file)
        except FileNotFoundError:
            try:
                with open("{0}.yml".format(filename)) as file:
                    return yaml.load(file, Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                LOGGER.exception('Invalid Yaml for %s.yml', filename)
            except FileNotFoundError:
                return {'Parameters': {}, 'Tags': {}}

    def _update_params(self, new_params, filename):
        """
        Responsible for updating the parameters within the files themself
        """
        with open("{0}/params/{1}.json".format(self.cwd, filename), 'w') as outfile:
            json.dump(new_params, outfile)

    def _determine_intrinsic_function(self, resolver, value, key):
        if str(value).startswith('resolve:'):
            return resolver.fetch_parameter_store_value(value, key)
        if str(value).startswith('import:'):
            return resolver.fetch_stack_output(value, key)
        if str(value).startswith('upload:'):
            return resolver.upload(value, key, self.file_name)
        return False

    def _determine_parameter_structure(self, parameters, resolver): # pylint: disable=inconsistent-return-statements
        try:
            for key, value in parameters.items():
                if isinstance(value, dict):
                    LOGGER.debug('Calling _determine_parameter_structure recursively')
                    return self._determine_parameter_structure(value, resolver)
                if self._determine_intrinsic_function(resolver, value, key):
                    continue
                resolver.update(key)
        except AttributeError:
            LOGGER.debug('Input was not a dict for _determine_parameter_structure, nothing to do.')
            pass

    def _param_updater(self, comparison_parameters, stage_parameters):
        """
        Generic Parameter Updater method
        """
        resolver = Resolver(self.parameter_store, stage_parameters, comparison_parameters)
        self._determine_parameter_structure(comparison_parameters, resolver)
        self._determine_parameter_structure(stage_parameters, resolver)
        return resolver.__dict__.get('stage_parameters')

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
