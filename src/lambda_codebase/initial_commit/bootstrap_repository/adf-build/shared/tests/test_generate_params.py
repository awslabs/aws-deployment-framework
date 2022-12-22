# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import shutil
import json
import os

from pytest import fixture, mark
from mock import Mock, patch
from generate_params import Parameters
from parameter_store import ParameterStore
from cloudformation import CloudFormation
from sts import STS


@fixture
def input_wave_target_one():
    return {
        'id': '111111111111',
        'name': 'account_name1',
        'path': '/one/path',
        'regions': ['eu-west-1'],
    }


@fixture
def input_wave_target_one_north():
    return {
        'id': '111111111111',
        'name': 'account_name1',
        'path': '/one/path',
        'regions': ['eu-north-1'],
    }


@fixture
def input_wave_target_one_us():
    return {
        'id': '111111111111',
        'name': 'account_name1',
        'path': '/one/path',
        'regions': ['us-east-1'],
    }


@fixture
def input_wave_target_two():
    return {
        'id': '222222222222',
        'name': 'account_name2',
        'path': '/two/path',
        'regions': ['eu-west-2'],
    }


@fixture
def input_wave_target_two_south():
    return {
        'id': '222222222222',
        'name': 'account_name2',
        'path': '/two/path',
        'regions': ['eu-south-1'],
    }


@fixture
def input_wave_target_two_us():
    return {
        'id': '222222222222',
        'name': 'account_name2',
        'path': '/two/path',
        'regions': ['us-west-2'],
    }


@fixture
def input_definition_targets(
    input_wave_target_one,
    input_wave_target_one_north,
    input_wave_target_one_us,
    input_wave_target_two,
    input_wave_target_two_south,
    input_wave_target_two_us,
):
    return [  # Waves are inside an array
        [  # Wave 1
            [  # Wave targets 1 - set 1
                input_wave_target_one,
                input_wave_target_two,
            ],
            [  # Wave targets 1 - set 2
                input_wave_target_one_north,
                input_wave_target_two_south,
            ],
        ],
        [  # Wave 2
            [  # Wave targets 2 - set 1
                input_wave_target_one_us,
            ],
            [  # Wave targets 2 - set 2
                input_wave_target_two_us,
            ],
        ],
    ]


@fixture
def cls():
    parameter_store = Mock()
    definition_s3 = Mock()
    definition_s3.read_object.return_value = json.dumps({
        'pipeline_input': {
            'environments': {
                'targets': [],
            }
        }
    })
    parameter_store.fetch_parameter.return_value = str({})
    parameters = Parameters(
        build_name='some_name',
        parameter_store=parameter_store,
        definition_s3=definition_s3,
        directory=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'stubs'
            )
        )
    )
    yield parameters
    # Skip the first slash
    shutil.rmtree(f'{parameters.cwd}/params')


def test_valid_build_name(cls):
    assert cls.build_name == 'some_name'


def test_params_folder_created(cls):
    assert os.path.exists(f'{cls.cwd}/params')


def test_retrieve_pipeline_targets_empty(cls):
    targets = cls._retrieve_pipeline_targets()
    assert targets == {}


def test_retrieve_pipeline_targets(cls, input_definition_targets):
    cls.definition_s3.read_object.return_value = json.dumps({
        'pipeline_input': {
            'environments': {
                'targets': input_definition_targets,
            }
        }
    })
    targets = cls._retrieve_pipeline_targets()
    assert targets['111111111111'] == {
        'id': '111111111111',
        'account_name': 'account_name1',
        'path': '/one/path',
        'regions': sorted(['eu-west-1', 'eu-north-1', 'us-east-1']),
    }
    assert targets['222222222222'] == {
        'id': '222222222222',
        'account_name': 'account_name2',
        'path': '/two/path',
        'regions': sorted(['eu-west-2', 'eu-south-1', 'us-west-2']),
    }
    assert list(targets.keys()) == [
        '111111111111',
        '222222222222',
    ]


@mark.parametrize("file, to_file, ext", [
    ('stub_cfn_global', 'global', 'json'),
    ('stub_cfn_global', 'global_yml', 'yml'),
])
def test_parse(cls, file, to_file, ext):
    shutil.copy(
        f"{cls.cwd}/{file}.{ext}",
        f"{cls.cwd}/params/{to_file}.{ext}",
    )
    parse = cls._parse(
        cls.cwd,
        to_file,
    )
    # Unresolved Intrinsic at this stage
    assert parse == {
        'Parameters': {
            'Environment': 'testing',
            'MySpecialValue': 'resolve:/values/some_value',
        },
        'Tags': {
            'CostCenter': 'overhead',
            'Department': 'unknown',
            'Geography': 'world',
        },
    }


def test_parse_not_found(cls):
    parse = cls._parse(
        cls.cwd,
        'nothing',
    )
    assert parse == {'Parameters': {}, 'Tags': {}}


def test_merge_params(cls):
    shutil.copy(
        f"{cls.cwd}/stub_cfn_global.json",
        f"{cls.cwd}/params/global.json",
    )
    with patch.object(
        ParameterStore,
        'fetch_parameter',
        return_value='something'
    ):
        parse = cls._parse(
            cls.cwd,
            'global',
        )
        compare = cls._merge_params(
            parse,
            {'Parameters': {}, 'Tags': {}}
        )
        assert compare == {
            'Parameters': {
                'Environment': 'testing',
                'MySpecialValue': 'something',
            },
            'Tags': {
                'CostCenter': 'overhead',
                'Department': 'unknown',
                'Geography': 'world',
            }
        }


def test_merge_params_with_preset(cls):
    shutil.copy(
        f"{cls.cwd}/stub_cfn_global.json",
        f"{cls.cwd}/params/global.json",
    )
    with patch.object(
        ParameterStore,
        'fetch_parameter',
        return_value='something'
    ):
        parse = cls._parse(
            cls.cwd,
            'global',
        )
        compare = cls._merge_params(
            parse,
            {
                'Parameters': {
                    'Base': 'Parameter',
                },
                'Tags': {
                    'CostCenter': 'should-not-be-overwritten',
                    'SomeBaseTag': 'BaseTag',
                },
            }
        )
        assert compare == {
            'Parameters': {
                'Base': 'Parameter',
                'Environment': 'testing',
                'MySpecialValue': 'something',
            },
            'Tags': {
                'CostCenter': 'should-not-be-overwritten',
                'Department': 'unknown',
                'Geography': 'world',
                'SomeBaseTag': 'BaseTag',
            }
        }


def test_create_parameter_files(cls, input_definition_targets):
    cls.definition_s3.read_object.return_value = json.dumps({
        'pipeline_input': {
            'environments': {
                'targets': input_definition_targets,
            }
        }
    })
    with patch.object(
        ParameterStore,
        'fetch_parameter',
        return_value='something',
    ):
        cls.create_parameter_files()
        assert os.path.exists(f"{cls.cwd}/params/account_name1_eu-west-1.json")
        assert os.path.exists(
            f"{cls.cwd}/params/account_name1_eu-north-1.json",
        )
        assert os.path.exists(f"{cls.cwd}/params/account_name1_us-east-1.json")
        assert os.path.exists(f"{cls.cwd}/params/account_name2_eu-west-2.json")
        assert os.path.exists(
            f"{cls.cwd}/params/account_name2_eu-south-1.json",
        )
        assert os.path.exists(f"{cls.cwd}/params/account_name2_us-west-2.json")


def test_ensure_parameter_default_contents(cls, input_definition_targets):
    cls.definition_s3.read_object.return_value = json.dumps({
        'pipeline_input': {
            'environments': {
                'targets': input_definition_targets,
            }
        }
    })
    shutil.copy(
        f"{cls.cwd}/stub_cfn_global.json",
        f"{cls.cwd}/params/global.json",
    )
    with patch.object(
        ParameterStore,
        'fetch_parameter',
        return_value='something',
    ):
        cls.create_parameter_files()

        parse = cls._parse(
            cls.cwd,
            "account_name1_us-east-1",
        )
        assert parse == {
            'Parameters': {
                'Environment': 'testing',
                'MySpecialValue': 'something',
            },
            'Tags': {
                'CostCenter': 'overhead',
                'Department': 'unknown',
                'Geography': 'world',
            }
        }


def test_ensure_parameter_overrides(
    cls,
    input_wave_target_one,
    input_wave_target_one_north,
    input_wave_target_two
):
    cls.definition_s3.read_object.return_value = json.dumps({
        'pipeline_input': {
            'environments': {
                'targets': [
                    [
                        [
                            input_wave_target_one,
                        ],
                        [
                            input_wave_target_one_north,
                        ],
                    ],
                    [
                        [
                            input_wave_target_two,
                        ],
                    ]
                ]
            }
        }
    })
    os.mkdir(f'{cls.cwd}/params/one')
    shutil.copy(
        f"{cls.cwd}/stub_cfn_global.json",
        f"{cls.cwd}/params/global.json",
    )
    shutil.copy(
        f"{cls.cwd}/parameter_environment_acceptance_tag_project_a.yml",
        f"{cls.cwd}/params/global_eu-west-1.yml",
    )
    shutil.copy(
        f"{cls.cwd}/tag_department_alpha_only.json",
        f"{cls.cwd}/params/one/path.json",
    )
    shutil.copy(
        f"{cls.cwd}/tag_geo_eu_only.json",
        f"{cls.cwd}/params/one/path_eu-west-1.json",
    )
    shutil.copy(
        f"{cls.cwd}/parameter_extra_one_only.json",
        f"{cls.cwd}/params/account_name1.json",
    )
    shutil.copy(
        f"{cls.cwd}/tag_cost_center_free_only.json",
        f"{cls.cwd}/params/account_name2_eu-west-2.json",
    )

    with patch.object(
        ParameterStore,
        'fetch_parameter',
        return_value='something',
    ):
        with patch.object(
            CloudFormation,
            'get_stack_output',
            return_value='something_else',
        ):
            with patch.object(
                STS,
                'assume_cross_account_role',
                return_value={},
            ):
                cls.create_parameter_files()
                assert (
                    cls._parse(
                        cls.cwd,
                        "account_name1_eu-west-1",
                    ) == {
                        'Parameters': {
                            'Environment': 'acceptance',  # Global region
                            'MySpecialValue': 'something',  # Global
                            'Extra': 'one',  # Account
                        },
                        'Tags': {
                            'CostCenter': 'overhead',  # Global
                            'Department': 'alpha',  # OU
                            'Geography': 'eu',  # OU Region
                            'Project': 'ProjectA',  # Global region
                        }
                    }
                )
                assert (
                    cls._parse(
                        cls.cwd,
                        "account_name1_eu-north-1",
                    ) == {
                        'Parameters': {
                            'Environment': 'testing',  # Global
                            'MySpecialValue': 'something',  # Global
                            'Extra': 'one',  # Account
                        },
                        'Tags': {
                            'CostCenter': 'overhead',  # Global
                            'Department': 'alpha',  # OU
                            'Geography': 'world',  # Global
                        }
                    }
                )
                assert (
                    cls._parse(
                        cls.cwd,
                        "account_name2_eu-west-2",
                    ) == {
                        'Parameters': {
                            'Environment': 'testing',  # Global
                            'MySpecialValue': 'something',  # Global
                        },
                        'Tags': {
                            'CostCenter': 'free',  # Account Region
                            'Department': 'unknown',  # Global
                            'Geography': 'world',  # Global
                        }
                    }
                )
