# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This file is pulled into CodeBuild containers
and used to build the parameters for CloudFormation stacks based on
param files in the params folder
"""

import re
from copy import deepcopy
import json
import secrets
# Not all string functions are deprecated, the ones we use are not.
# Hence disabling the lint finding:
from string import ascii_lowercase, digits  # pylint: disable=deprecated-module
import os
from itertools import chain
from typing import Dict, Iterator, List, Optional, Union
from typing_extensions import TypedDict
import yaml
import boto3

from logger import configure_logger
from parameter_store import ParameterStore
from resolver import Resolver
from s3 import S3


class ParametersAndTags(TypedDict):
    """
    The param files will have Parameters and Tags, where these are
    """
    Parameters: Dict[str, str]
    Tags: Dict[str, str]


# When the wave target is selecting accounts using a
# tag based selection, where the key and value should be
# defined in the account:
TagKeyDict = Dict[str, str]

# A wave target path can be a string referencing the account id,
# the organization unit path, or a tag based selection using TagKeyDict.
WaveTargetPath = Union[str, TagKeyDict]


class ParamGenWaveTarget(TypedDict):
    """
    Optimized parameter generation wave target with clearly
    identified fields as used in the generate parameters process.
    """
    id: str
    account_name: str
    path: WaveTargetPath
    regions: List[str]


# When the pipeline targets are retrieved, it will create a dictionary
# where they key will reference the account id and the value will
# contain all the relevant information of the wave target.
# The ParamGenWaveTarget will contain all the information from the
# different ParamGenWaveTarget it found that reference the same account id.
#
# In other words, if account A is targeted in the first wave for region
# eu-west-1 and it is targeted in the second wave in us-east-1, the combined
# ParamGenWaveTarget will contain both regions in the `regions` attribute.
PipelineTargets = Dict[str, ParamGenWaveTarget]


class InputPipelineWaveTarget(TypedDict):
    """
    Each wave target in a pipeline will have the following
    fields to point to the target account.
    """
    id: str
    name: str
    path: WaveTargetPath
    regions: List[str]


# When defining the pipeline, the accounts that it deploys to are mapped
# in waves. Within each wave, it will contain a list of wave targets to
# make sure that referencing 100 accounts for example will be broken down
# into two waves of 50 accounts each as max supported by CodePipeline.
TargetWavesWithNestedWaveTargets = List[  # Waves
    List[  # Wave Targets
        InputPipelineWaveTarget
    ]
]


class InputEnvironmentDefinition(TypedDict):
    """
    Inside the pipeline input environment, the list of targets
    is defined as a list of waves that each contain a list of wave targets.
    """
    targets: TargetWavesWithNestedWaveTargets


class InputDefinition(TypedDict):
    """
    The input of the pipeline definition holds the environment
    with all the targets defined inside.
    """
    environment: InputEnvironmentDefinition


class PipelineDefinition(TypedDict):
    """
    Bare minimum input pipeline definition as required for traversal
    in this generation of parameters.
    """
    input: InputDefinition


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]
EMPTY_PARAMS_DICT: ParametersAndTags = {'Parameters': {}, 'Tags': {}}
ADF_ORG_STAGE = os.getenv("ADF_ORG_STAGE", "dev")


class Parameters:
    """
    Parameter generation class.
    """
    def __init__(
        self,
        build_name: str,
        parameter_store: ParameterStore,
        definition_s3: S3,
        directory: Optional[str] = None,
    ):
        self.cwd = directory or os.getcwd()
        self._create_params_folder()
        self.resolver = Resolver(parameter_store)
        self.build_name = build_name
        self.definition_s3 = definition_s3
        self.file_name = "".join(
            secrets.choice(ascii_lowercase + digits)
            for _ in range(6)
        )

    def _retrieve_pipeline_definition(self) -> PipelineDefinition:
        return json.loads(
            self.definition_s3.read_object(
                f"pipelines/{self.build_name}/definition.json",
            ),
        )

    def _retrieve_pipeline_targets(self) -> PipelineTargets:
        pipeline_targets = {}
        pipeline_definition = self._retrieve_pipeline_definition()
        pipeline_input_key = (
            # Support to fallback to 'input' definition key.
            # This is scheduled to be deprecated in v4.0
            "pipeline_input" if "pipeline_input" in pipeline_definition
            else "input"
        )
        input_targets: TargetWavesWithNestedWaveTargets = (
            pipeline_definition[pipeline_input_key]['environments']['targets']
        )
        # Since the input_targets returns a list of waves that each contain
        # a list of wave_targets, we need to flatten them to iterate:
        wave_targets: Iterator[ParamGenWaveTarget] = map(
            lambda wt: {
                # Change wt: InputPipelineWaveTarget to ParamGenWaveTarget
                'id': wt['id'],
                'account_name': wt['name'],
                'path': wt['path'],
                'regions': wt['regions'],
            },
            filter(
                lambda wt: wt['id'] != 'approval',
                # Flatten the three levels of nested arrays to one iterable:
                chain.from_iterable(
                    chain.from_iterable(
                        input_targets,
                    ),
                ),
            )  # Returns an Iterator[InputPipelineWaveTarget]
        )
        for wave_target in wave_targets:
            if wave_target['id'] in pipeline_targets:
                # Lets merge the regions to show what regions it deploys
                # to
                stored_target = pipeline_targets[wave_target['id']]
                stored_target['regions'] = sorted(list(set(
                    stored_target['regions']
                    + wave_target['regions'],
                )))
            else:
                pipeline_targets[wave_target['id']] = wave_target
        # Returns a list of targets:
        # [
        #   {
        #     "id": "111111111111",
        #     "account_name": "account-name",
        #     "path": "/ou/path" | "1111111111" | { "TagKey": "TagValue" }
        #     "regions": [ "eu-west-1", "us-east-1", "etc" ]
        #   },
        #   ...
        # ]
        LOGGER.debug(
            "Found the following pipeline targets: %s",
            pipeline_targets,
        )
        return pipeline_targets

    def _create_params_folder(self) -> None:
        try:
            dir_path = f'{self.cwd}/params'
            os.mkdir(dir_path)
            LOGGER.debug("Created directory: %s", dir_path)
        except FileExistsError:
            pass

    def create_parameter_files(self) -> None:
        """
        Iterates over the pipeline target, and for each account it targets
        it will iterate over the regions to which it deploys in that account
        to generate the parameter files for those.

        The parameter files are generated with most specific parameter
        definition winning. It iterates over the following files:
            1. f"{account_name}_{region}" i.e. "security-account_eu-west-1"
            1. f"{account_name}" i.e. "security-account"
            1. f"{organization_unit_path}_{region}"
                i.e. "/devsecops/security_eu-west-1"
            1. f"{organization_unit_path}" i.e. "/devsecops/security"
            1. f"{global}_{region}" i.e. "global_eu-west-1"
            1. f"{global}_{stage}" i.e. "global_dev"
            1. f"{global}" i.e. "global"

        It will then generate a JSON file that holds all the parameters per
        target/region combination as such: "{account_name}_{region}.json"

        It will add new parameters or tags if the parameter or tag is found in
        a less specific file, and it was missing in the more specific files
        it processed so far. For example, if the account_region file did not
        include the Department Tag, while the account file does, it will get
        included automatically. If you want to override the Department key in a
        specific region, make sure to include that in the account_region in
        this case.
        """
        for target in self._retrieve_pipeline_targets().values():
            for region in target['regions']:
                LOGGER.debug(
                    "Generating parameters for the %s account in %s",
                    target['account_name'],
                    region,
                )
                current_params = deepcopy(EMPTY_PARAMS_DICT)
                current_params = self._merge_params(
                    Parameters._parse(
                        params_root_path=self.cwd,
                        params_filename=f"{target['account_name']}_{region}",
                    ),
                    current_params,
                )
                current_params = self._merge_params(
                    Parameters._parse(
                        params_root_path=self.cwd,
                        params_filename=target['account_name'],
                    ),
                    current_params,
                )
                path_references_ou = (
                    isinstance(target['path'], str)
                    and not Parameters._is_account_id(target['path'])
                )
                if path_references_ou:
                    # Compare account_region final to ou_region
                    ou_id_or_path = target['path']
                    if ou_id_or_path.startswith('/'):
                        # Skip the first slash
                        ou_id_or_path = ou_id_or_path[1:]
                    # Cleanup the ou name to include only alphanumeric, dashes,
                    # and underscores:
                    current_params = self._merge_params(
                        Parameters._parse(
                            params_root_path=self.cwd,
                            params_filename=f"{ou_id_or_path}_{region}",
                        ),
                        current_params
                    )
                    # Compare account_region final to ou
                    current_params = self._merge_params(
                        Parameters._parse(
                            params_root_path=self.cwd,
                            params_filename=ou_id_or_path,
                        ),
                        current_params
                    )
                # Compare account_region final to deployment_account_region
                current_params = self._merge_params(
                    Parameters._parse(
                        params_root_path=self.cwd,
                        params_filename=f"global_{region}",
                    ),
                    current_params
                )
                # Compare account_region final to global_stage
                adf_org_stage = ADF_ORG_STAGE # Fetch from Environ for Start
                current_params = self._merge_params(
                    Parameters._parse(
                        params_root_path=self.cwd,
                        params_filename=f"global_{adf_org_stage}",
                    ),
                    current_params
                )
                # Compare account_region final to global
                current_params = self._merge_params(
                    Parameters._parse(
                        params_root_path=self.cwd,
                        params_filename="global",
                    ),
                    current_params
                )
                if current_params:
                    self._write_params(
                        current_params,
                        f"{target['account_name']}_{region}",
                    )

    @staticmethod
    def _is_account_id(wave_target_path: WaveTargetPath) -> bool:
        return str(wave_target_path).isnumeric()

    @staticmethod
    def _clean_params_filename(params_filename: str) -> str:
        # Cleanup the params_filename to include only alphanumeric, dashes,
        # slashes, and underscores:
        return re.sub(r'[^0-9a-zA-Z_\-/]+', '_', params_filename)

    @staticmethod
    def _parse(
        params_root_path: str,
        params_filename: str,
    ) -> ParametersAndTags:
        """
        Attempt to parse the parameters file and return the default
        CloudFormation parameter base object if not found. Returning
        Base CloudFormation Parameters here since if the user was using
        Any other type (SC, ECS) they would require a parameter file
        (global.json) and thus this would not fail.

        Args:
            params_root_path (str): The root path where the `params` folder is
                located in.
            params_filename (str): The name of the parameter file without the
                file extension. For example `global` will attempt to read
                f"{params_root_path}/params/{params_filename}.json"
                and if that fails it will try to read:
                f"{params_root_path}/params/{params_filename}.yml"

        Returns
            ParametersAndTags: The Parameters and Tags defined in the file.
        """
        clean_file_name = Parameters._clean_params_filename(
            params_filename,
        )
        file_path = f"{params_root_path}/params/{clean_file_name}"
        try:
            with open(f"{file_path}.json", encoding='utf-8') as file:
                json_content = json.load(file)
                LOGGER.debug(
                    "Read %s.yml: %s",
                    file_path,
                    json_content,
                )
                return json_content
        except FileNotFoundError:
            try:
                with open(f"{file_path}.yml", encoding='utf-8') as file:
                    yaml_content = yaml.load(file, Loader=yaml.FullLoader)
                    LOGGER.debug(
                        "Read %s.yml: %s",
                        file_path,
                        yaml_content,
                    )
                    return yaml_content
            except yaml.scanner.ScannerError:
                LOGGER.exception('Invalid Yaml for %s.yml', file_path)
                raise
            except FileNotFoundError:
                LOGGER.debug(
                    "File not found for %s.{json or yml}, defaulting to empty",
                    file_path,
                )
                return {'Parameters': {}, 'Tags': {}}

    def _write_params(
        self,
        new_params: ParametersAndTags,
        filename: str,
    ) -> None:
        """
        Responsible for writing the parameters within the files themselves

        Args:
            new_params (ParametersAndTags): The Parameters and Tags to write
                to the requested file.
            filename (str): The name of the file to write to inside the params
                folder.
        """
        filepath = f"{self.cwd}/params/{filename}.json"
        LOGGER.debug(
            "Writing to parameter file: %s: %s",
            filepath,
            new_params,
        )
        with open(filepath, mode='w', encoding='utf-8') as outfile:
            json.dump(new_params, outfile)

    def _merge_params(
        self,
        new_params: ParametersAndTags,
        current_params: ParametersAndTags
    ) -> ParametersAndTags:
        """
        Merge the new_params Parameters and Tags found into a clone of the
        current_params if the Parameter or Tag found in the new_params is not
        present in the current_params yet. Or the current_params version of
        that Parameter or Tag is an empty string.

        Args:
            new_params (ParametersAndTags): The new Parameters and Tags to
                merge into the current_params.
            current_params (ParametersAndTags): The current Parameters and Tags
                which is cloned and returned with the new parameters and tags
                it found in new_params. Unless current_params already
                contained the Parameter or Tag, as described above.

        Returns:
            ParametersAndTags: A clone of the current_params and newly merged
                Parameters and Tags.
        """
        merged_params = deepcopy(current_params)
        for root_key in new_params:
            if root_key not in merged_params:
                merged_params[root_key] = {}
            for key in new_params[root_key]:
                if merged_params[root_key].get(key, '') == '':
                    merged_params[root_key][key] = (
                        self.resolver.apply_intrinsic_function_if_any(
                            new_params[root_key][key],
                            self.file_name,
                        )
                    )
        LOGGER.debug(
            "Merged result %s",
            merged_params,
        )
        return merged_params


def main() -> None:
    """
    Main method that is invoked when the generate params script is executed.
    """
    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    definition_bucket_name = parameter_store.fetch_parameter(
        "/adf/pipeline_definition_bucket",
    )
    definition_s3 = S3(DEPLOYMENT_ACCOUNT_REGION, definition_bucket_name)
    parameters = Parameters(
        PROJECT_NAME,
        parameter_store,
        definition_s3,
    )
    parameters.create_parameter_files()


if __name__ == '__main__':
    main()
