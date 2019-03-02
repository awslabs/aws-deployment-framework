# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file


from pytest import fixture
from event import Event
from mock import Mock
from .stubs import event


@fixture
def cls():
    parameter_store = Mock()
    parameter_store.fetch_parameter.return_value = str(event.stub_config)

    organizations = Mock()
    organizations.describe_ou_name.return_value = 'some_ou_name'
    organizations.build_account_path.return_value = 'some_ou_path'
    organizations.get_organization_info.return_value = {
        "organization_master_account_id": "12345678910",
        "organization_id": "id-123"
    }

    return Event(
        event=event.stub_event,
        parameter_store=parameter_store,
        organizations=organizations,
        account_id=111111111111
    )


def test_event_is_deployment_account(cls):
    assert cls.is_deployment_account == 0


def test_event_is_not_moved_to_root(cls):
    assert cls.moved_to_root == 0


def test_event_destination_ou_id(cls):
    assert cls.destination_ou_id == 'ou-a9ny-ggggggg'


def test_event_moved_to_protected(cls):
    assert cls.moved_to_protected is 0


def test_event_destination_ou_name(cls):
    assert cls.destination_ou_name is None


def test_event_protected_ou_list(cls):
    assert cls.protected_ou_list == []


def test_determine_if_deployment_account(cls):
    cls._determine_if_deployment_account()
    assert cls.is_deployment_account is 0


def test_set_destination_ou_name(cls):
    cls.set_destination_ou_name()
    assert cls.destination_ou_name == 'some_ou_name'


def test_create_deployment_account_parameters(cls):
    assertion = cls.create_deployment_account_parameters()
    assert assertion.get('master_account_id') == '12345678910'
    assert assertion.get('organization_id') == 'id-123'


def test_create_output_object(cls):
    assertion = cls.create_output_object({})
    assert assertion.get('account_id') == 111111111111
    assert assertion.get('is_deployment_account') is 0


def test_ensure_deployment_order_multiple(cls):
    cls.regions = ['region2', 'region1']
    cls.deployment_account_region = 'region1'
    cls._ensure_deployment_order()
    assert cls.regions[0] == 'region1'
    assert cls.regions[1] == 'region2'


def test_ensure_deployment_order_single(cls):
    cls.regions = ['region1']
    cls.deployment_account_region = 'region1'
    cls._ensure_deployment_order()
    assert cls.regions[0] == 'region1'
