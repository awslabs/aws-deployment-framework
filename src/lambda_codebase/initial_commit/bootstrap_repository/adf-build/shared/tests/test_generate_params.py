# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import shutil
import os
import boto3
import sys

from pytest import fixture
from mock import Mock, patch
from cache import Cache
from generate_params import Parameters
from parameter_store import ParameterStore
from cloudformation import CloudFormation
from sts import STS
from resolver import Resolver

@fixture
def cls():
    parameter_store = Mock()
    parameter_store.fetch_parameter.return_value = str({})
    parameters = Parameters(
        build_name='some_name',
        parameter_store=parameter_store,
        directory=os.path.abspath(os.path.join(os.path.dirname(__file__), 'stubs'))
    )
    parameters.account_ous = {'account_name1': '/banking/testing', 'account_name2': '/banking/production'}
    parameters.regions = ['eu-west-1', 'eu-central-1', 'us-west-2']
    yield parameters
    shutil.rmtree('{0}/params'.format(parameters.cwd))


def test_valid_build_name(cls):
    assert cls.build_name == 'some_name'


def test_params_folder_created(cls):
    assert os.path.exists('{0}/params'.format(cls.cwd))


def test_parse(cls):
    parse = cls._parse(
        '{0}/stub_cfn_global'.format(cls.cwd)
    )
    # Unresolved Intrinsic at this stage
    assert parse == {'Parameters': {'CostCenter': '123', 'Environment': 'testing', 'MySpecialValue': 'resolve:/values/some_value'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}


def test_parse_not_found(cls):
    parse = cls._parse(
        '{0}/nothing'.format(cls.cwd)
    )
    assert parse == {'Parameters': {}, 'Tags': {}}


def test_param_updater(cls):
    with patch.object(ParameterStore, 'fetch_parameter', return_value='something') as ssm_mock:
        parse = cls._parse(
            '{0}/stub_cfn_global'.format(cls.cwd)
        )
        compare = cls._param_updater(
            parse,
            {'Parameters': {}, 'Tags': {}}
        )
        assert compare == {'Parameters': {'CostCenter': '123', 'Environment': 'testing', 'MySpecialValue': 'something'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}

    #assert compare == {'Parameters': {'CostCenter': 'not_free', 'Environment': 'testing', 'MySpecialValue': 'something'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}


def test_create_parameter_files(cls):
    with patch.object(ParameterStore, 'fetch_parameter', return_value='something') as ssm_mock:
        cls.global_path = "{0}/stub_cfn_global".format(cls.cwd)
        cls.create_parameter_files()
        assert os.path.exists("{0}/params/account_name1_eu-west-1.json".format(cls.cwd))
        assert os.path.exists("{0}/params/account_name1_eu-central-1.json".format(cls.cwd))
        assert os.path.exists("{0}/params/account_name1_us-west-2.json".format(cls.cwd))
        assert os.path.exists("{0}/params/account_name2_eu-west-1.json".format(cls.cwd))
        assert os.path.exists("{0}/params/account_name2_eu-central-1.json".format(cls.cwd))
        assert os.path.exists("{0}/params/account_name2_us-west-2.json".format(cls.cwd))


def test_ensure_parameter_default_contents(cls):
    with patch.object(ParameterStore, 'fetch_parameter', return_value='something') as ssm_mock:
        cls.global_path = "{0}/stub_cfn_global".format(cls.cwd)
        cls.create_parameter_files()

        parse = cls._parse(
            "{0}/params/account_name1_us-west-2".format(cls.cwd)
        )
        assert parse == {'Parameters': {'CostCenter': '123', 'Environment': 'testing', 'MySpecialValue': 'something'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}


def test_ensure_parameter_specific_contents(cls):
    cls.global_path = "{0}/stub_cfn_global".format(cls.cwd)
    shutil.copy(
        "{0}/account_name1_eu-west-1.json".format(cls.cwd),
        "{0}/params/account_name1_eu-west-1.json".format(cls.cwd)
    )
    shutil.copy(
        "{0}/account_name1_eu-central-1.yml".format(cls.cwd),
        "{0}/params/account_name1_eu-central-1.yml".format(cls.cwd)
    )

    with patch.object(ParameterStore, 'fetch_parameter', return_value='something') as ssm_mock:
        with patch.object(CloudFormation, 'get_stack_output', return_value='something_else') as cfn_mock:
            with patch.object(STS, 'assume_cross_account_role', return_value={}) as sts_mock:
                cls.create_parameter_files()
                parse_json = cls._parse(
                    "{0}/params/account_name1_eu-west-1".format(cls.cwd)
                )
                parse_yml = cls._parse(
                    "{0}/params/account_name1_eu-central-1".format(cls.cwd)
                )
                assert parse_json == {'Parameters': {'CostCenter': 'free', 'MySpecialValue': 'something', 'Environment': 'testing'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}
                assert parse_yml == {'Parameters': {'CostCenter': 'not_free', 'MySpecialValue': 'something', 'Environment': 'testing'}, 'Tags': {'TagKey': '123', 'MyKey': 'new_value'}}
