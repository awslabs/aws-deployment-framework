# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Tests for schema validation
"""

import unittest
import schema_validation
from schema import Schema, SchemaError


class NotificationSchemaValidationHappyPaths(unittest.TestCase):
    def test_notification_props_schema_lambda(self):
        notification_props = {"target": "my_cool_target", "type": "lambda"}
        self.assertDictEqual(
            Schema(schema_validation.NOTIFICATION_PROPS).validate(notification_props),
            notification_props,
        )

    def test_notification_props_schema_chatbot(self):
        notification_props = {"target": "my_cool_target", "type": "chat_bot"}
        self.assertDictEqual(
            Schema(schema_validation.NOTIFICATION_PROPS).validate(notification_props),
            notification_props,
        )

    def test_param_schema_default(self):
        param_props = {
            "notification_endpoint": "a_notification_endpoint",
            "schedule": "a_schedule_string",
            "restart_execution_on_update": True,
        }

        expected_response = {**param_props, "pipeline_type": "default"}

        self.assertDictEqual(
            Schema(schema_validation.PARAM_SCHEMA).validate(param_props),
            expected_response,
        )

    def test_param_schema_pipeline_type(self):
        param_props = {
            "notification_endpoint": "a_notification_endpoint",
            "schedule": "a_schedule_string",
            "restart_execution_on_update": True,
            "pipeline_type": "default",
        }
        self.assertDictEqual(
            Schema(schema_validation.PARAM_SCHEMA).validate(param_props),
            param_props,
        )

    def test_param_schema_pipeline_type_with_notification_props(self):
        param_props = {
            "notification_endpoint": {
                "target": "#slackchannel",
                "type": "chat_bot",
            },
            "schedule": "a_schedule_string",
            "restart_execution_on_update": True,
            "pipeline_type": "default",
        }
        self.assertDictEqual(
            Schema(schema_validation.PARAM_SCHEMA).validate(param_props),
            param_props,
        )


class CodeCommitSchemaValidationHappyPaths(unittest.TestCase):
    def test_codecommit_source_props_schema_default(self):
        codecommit_props = {
            "account_id": "111111111111",
            "repository": "a_repo_name",
            "branch": "mainline",
            "poll_for_changes": True,
            "owner": "a_repo_owner",
            "role": "a_role_name",
            "trigger_on_changes": True,
        }
        expected_result = {**codecommit_props, "output_artifact_format": None}
        self.assertDictEqual(
            Schema(schema_validation.CODECOMMIT_SOURCE_PROPS).validate(
                codecommit_props
            ),
            expected_result,
        )

    def test_codecommit_source_props_schema_output_format_clone_ref(self):
        codecommit_props = {
            "account_id": "111111111111",
            "repository": "a_repo_name",
            "branch": "mainline",
            "poll_for_changes": True,
            "owner": "a_repo_owner",
            "role": "a_role_name",
            "trigger_on_changes": True,
            "output_artifact_format": "CODEBUILD_CLONE_REF",
        }
        self.assertDictEqual(
            Schema(schema_validation.CODECOMMIT_SOURCE_PROPS).validate(
                codecommit_props
            ),
            codecommit_props,
        )

    def test_codecommit_source_props_schema_output_format_code_zip(self):
        codecommit_props = {
            "account_id": "111111111111",
            "repository": "a_repo_name",
            "branch": "mainline",
            "poll_for_changes": True,
            "owner": "a_repo_owner",
            "role": "a_role_name",
            "trigger_on_changes": True,
            "output_artifact_format": "CODE_ZIP",
        }
        self.assertDictEqual(
            Schema(schema_validation.CODECOMMIT_SOURCE_PROPS).validate(
                codecommit_props
            ),
            codecommit_props,
        )

    def test_codecommit_source_schema(self):
        codecommit_props = {
            "account_id": "111111111111",
            "repository": "a_repo_name",
            "branch": "mainline",
            "poll_for_changes": True,
            "owner": "a_repo_owner",
            "role": "a_role_name",
            "trigger_on_changes": True,
            "output_artifact_format": "CODE_ZIP",
        }
        codecommit_source = {"provider": "codecommit", "properties": codecommit_props}
        self.assertDictEqual(
            Schema(schema_validation.CODECOMMIT_SOURCE).validate(codecommit_source),
            codecommit_source,
        )


class CodeConnectionsSchemaValidationHappyPaths(unittest.TestCase):
    def test_codeconnections_source_props_schema_default(self):
        source_props = {
            "repository": "a_repo_name",
            "branch": "mainline",
            "owner": "a_repo_owner",
            "codeconnections_param_path": "the_ssm_param_connection_path",
            "output_artifact_format": "CODE_ZIP",
        }
        self.assertDictEqual(
            Schema(schema_validation.CODECONNECTIONS_SOURCE_PROPS).validate(source_props),
            source_props,
        )

    def test_codeconnections_source_schema_default(self):
        source_props = {
            "repository": "a_repo_name",
            "branch": "mainline",
            "owner": "a_repo_owner",
            "codeconnections_param_path": "the_ssm_param_connection_path",
            "output_artifact_format": "CODE_ZIP",
        }

        codeconnections_source = {"provider": "codeconnections", "properties": source_props}

        self.assertDictEqual(
            Schema(schema_validation.CODECONNECTIONS_SOURCE).validate(codeconnections_source),
            codeconnections_source,
        )

    def test_codeconnections_source_schema_required_only(self):
        source_props = {
            "owner": "a_repo_owner",
            "codeconnections_param_path": "the_ssm_param_connection_path",
        }

        codeconnections_source = {"provider": "codeconnections", "properties": source_props}

        self.assertDictEqual(
            Schema(schema_validation.CODECONNECTIONS_SOURCE).validate(codeconnections_source),
            {
                "provider": "codeconnections",
                "properties": {
                    **codeconnections_source["properties"],
                    "output_artifact_format": None,
                }
            },
        )


class TargetSchemaValidationHappyPaths(unittest.TestCase):
    def test_target_list_schema_list(self):
        target_value = ["11111111111", "2222222222"]
        self.assertEqual(
            Schema(schema_validation.TARGET_LIST_SCHEMA).validate(target_value),
            target_value,
        )

    def test_target_list_wave_schema_default(self):
        wave_schema = {"size": 50}
        self.assertDictEqual(
            Schema(schema_validation.TARGET_WAVE_SCHEME).validate({}),
            wave_schema,
        )

    def test_target_list_wave_schema_with_value(self):
        wave_schema = {"size": 30}
        self.assertDictEqual(
            Schema(schema_validation.TARGET_WAVE_SCHEME).validate(wave_schema),
            wave_schema,
        )

    def test_target_schema_defaults(self):
        target_schema = {"wave": {"size": 50}, "exclude": []}
        self.assertDictEqual(
            Schema(schema_validation.TARGET_SCHEMA).validate({}),
            target_schema,
        )

    def test_target_schema_configured_path(self):
        target_schema = {
            "path": [
                "/some_org/production/banking",
            ],
            "wave": {
                "size": 50,
            },
            "exclude": [],
        }
        self.assertDictEqual(
            Schema(schema_validation.TARGET_SCHEMA).validate(target_schema),
            target_schema,
        )

    def test_target_schema_configured_path_for_recursive_ous(self):
        target_schema = {
            "path": [
                "/some_org/production/*",
            ],
            "wave": {
                "size": 50,
            },
            "exclude": ["/some_org/production/"],
        }
        self.assertDictEqual(
            Schema(schema_validation.TARGET_SCHEMA).validate(target_schema),
            target_schema,
        )


class PipelineSchemaValidationHappyPaths(unittest.TestCase):
    def test_codecommit_source_props_schema_without_account_id(self):
        codecommit_props = {
            "repository": "a_repo_name",
            "branch": "mainline",
        }
        expected_result = {**codecommit_props, "output_artifact_format": None}
        self.assertDictEqual(
            Schema(schema_validation.CODECOMMIT_SOURCE_PROPS).validate(
                codecommit_props
            ),
            expected_result,
        )

    def test_pipeline_with_codecommit_source_without_account_id(self):
        map_input = {
            "pipelines": [
                {
                    "name": "a_pipeline",
                    "default_providers": {
                        "source": {
                            "provider": "codecommit",
                            "properties": {
                                "repository": "a_repo_name",
                            },
                        },
                    },
                },
            ],
        }
        validated = schema_validation.SchemaValidation(map_input).validated
        self.assertEqual(
            validated["pipelines"][0]["default_providers"]["source"][
                "properties"
            ],
            {
                "repository": "a_repo_name",
            },
        )

    def test_pipeline_without_build_block(self):
        map_input = {
            "pipelines": [
                {
                    "name": "a_pipeline",
                    "default_providers": {
                        "source": {
                            "provider": "codecommit",
                            "properties": {
                                "account_id": "111111111111",
                            },
                        },
                    },
                },
            ],
        }
        validated = schema_validation.SchemaValidation(map_input).validated
        self.assertNotIn(
            "build",
            validated["pipelines"][0]["default_providers"],
        )


class PipelineSchemaValidationUnhappyPaths(unittest.TestCase):
    def test_pipeline_with_malformed_codecommit_account_id(self):
        map_input = {
            "pipelines": [
                {
                    "name": "a_pipeline",
                    "default_providers": {
                        "source": {
                            "provider": "codecommit",
                            "properties": {
                                "account_id": "not_an_account_id",
                            },
                        },
                    },
                },
            ],
        }
        with self.assertRaises(SchemaError):
            schema_validation.SchemaValidation(map_input)

    def test_pipeline_with_malformed_build_block(self):
        map_input = {
            "pipelines": [
                {
                    "name": "a_pipeline",
                    "default_providers": {
                        "source": {
                            "provider": "codecommit",
                            "properties": {
                                "account_id": "111111111111",
                            },
                        },
                        "build": {
                            "provider": "not_a_valid_build_provider",
                        },
                    },
                },
            ],
        }
        with self.assertRaises(SchemaError):
            schema_validation.SchemaValidation(map_input)
