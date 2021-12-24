# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the parameters for CloudFormation stacks based on
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
from s3 import S3
from logger import configure_logger
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
SHARED_MODULES_BUCKET = os.environ["S3_BUCKET_NAME"]
PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]

class Parameters:
    def __init__(self, build_name, parameter_store, s3, directory=None):
        self.cwd = directory or os.getcwd()
        self._create_params_folder()
        self.global_path = "params/global"
        self.parameter_store = parameter_store
        self.build_name = build_name
        self.s3 = s3
        self.file_name = "".join(
            secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6)
        )
        [self.account_ous, self.regions] = self._fetch_initial_parameter()

    def _fetch_initial_parameter(self):
        return [
            ast.literal_eval(
                self.s3.read_object(f"adf-parameters/deployment/{self.build_name}/account_ous.json")
            ),
            ast.literal_eval(
                self.parameter_store.fetch_parameter(f"/deployment/{self.build_name}/regions")
            )
        ]

    def _create_params_folder(self):
        try:
            return os.mkdir(f'{self.cwd}/params')
        except FileExistsError:
            return None

    @staticmethod
    def _is_account_id(value):
        return str(value).isnumeric()

    def create_parameter_files(self):
        for account, ou in self.account_ous.items():
            for region in self.regions:
                compare_params = {'Parameters': {}, 'Tags': {}}
                compare_params = self._param_updater(
                    Parameters._parse(f"{self.cwd}/params/{account}_{region}"),
                    compare_params,
                )
                compare_params = self._param_updater(
                    Parameters._parse(f"{self.cwd}/params/{account}"),
                    compare_params,
                )
                if not Parameters._is_account_id(ou):
                    # Compare account_region final to ou_region
                    compare_params = self._param_updater(
                        Parameters._parse(f"{self.cwd}/params/{ou}_{region}"),
                        compare_params
                    )
                    # Compare account_region final to ou
                    compare_params = self._param_updater(
                        Parameters._parse(f"{self.cwd}/params/{ou}"),
                        compare_params
                    )
                # Compare account_region final to deployment_account_region
                compare_params = self._param_updater(
                    Parameters._parse(f"{self.cwd}/params/global_{region}"),
                    compare_params
                )
                # Compare account_region final to global
                compare_params = self._param_updater(
                    Parameters._parse(self.global_path),
                    compare_params
                )
                if compare_params is not None:
                    self._update_params(compare_params, f"{account}_{region}")

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
            with open(f"{filename}.json", encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            try:
                with open(f"{filename}.yml", encoding='utf-8') as file:
                    return yaml.load(file, Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                LOGGER.exception('Invalid Yaml for %s.yml', filename)
                raise
            except FileNotFoundError:
                return {'Parameters': {}, 'Tags': {}}

    def _update_params(self, new_params, filename):
        """
        Responsible for updating the parameters within the files themselves
        """
        with open(f"{self.cwd}/params/{filename}.json", mode='w', encoding='utf-8') as outfile:
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
    s3 = S3(DEPLOYMENT_ACCOUNT_REGION, SHARED_MODULES_BUCKET)
    parameters = Parameters(
        PROJECT_NAME,
        ParameterStore(
            DEPLOYMENT_ACCOUNT_REGION,
            boto3
        ),
        s3
    )
    parameters.create_parameter_files()


if __name__ == '__main__':
    main()
