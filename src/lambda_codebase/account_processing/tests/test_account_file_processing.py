# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Tests the account file processing lambda
"""
import unittest
from ..process_account_files import (
    process_account,
    process_account_list,
    get_details_from_event,
    sanitize_account_name_for_snf,
)


class SuccessTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_process_account_when_account_exists(self):
        test_account = {
            "alias": "MyCoolAlias",
            "account_full_name": "myTestAccountName",
        }
        account_lookup = {"myTestAccountName": 123456789012}
        self.assertDictEqual(
            process_account(account_lookup, test_account),
            {
                "alias": "MyCoolAlias",
                "account_full_name": "myTestAccountName",
                "account_id": 123456789012,
                "needs_created": False,
            },
        )

    def test_process_account_when_account_does_not_exist(self):
        test_account = {
            "alias": "MyCoolAlias",
            "account_full_name": "myTestAccountName",
        }
        account_lookup = {"myDifferentAccount": 123456789012}
        self.assertDictEqual(
            process_account(account_lookup, test_account),
            {
                "alias": "MyCoolAlias",
                "account_full_name": "myTestAccountName",
                "needs_created": True,
            },
        )

    def test_process_account_list(self):
        all_accounts = [{"Name": "myTestAccountName", "Id": 123456789012}]
        accounts_in_file = [
            {"account_full_name": "myTestAccountName"},
            {"account_full_name": "myNewAccountName"},
        ]
        self.assertListEqual(
            process_account_list(all_accounts, accounts_in_file),
            [
                {
                    "account_full_name": "myTestAccountName",
                    "needs_created": False,
                    "account_id": 123456789012,
                },
                {
                    "account_full_name": "myNewAccountName",
                    "needs_created": True,
                },
            ],
        )

    def test_get_sanitize_account_name(self):
        self.assertEqual(
            sanitize_account_name_for_snf("myTestAccountName"), "myTestAccountName"
        )
        self.assertEqual(
            sanitize_account_name_for_snf(
                "thisIsALongerAccountNameForTestingTruncatedNames"
            ),
            "thisIsALongerAccountNameForTes",
        )
        self.assertEqual(
            sanitize_account_name_for_snf(
                "thisIsALongerAccountName ForTestingTruncatedNames"
            ),
            "thisIsALongerAccountName_ForTe",
        )
        self.assertEqual(
            sanitize_account_name_for_snf("this accountname <has illegal> chars"),
            "this_accountname__has_illegal_",
        )
        self.assertEqual(
            sanitize_account_name_for_snf("this accountname \\has illegal"),
            "this_accountname__has_illegal",
        )
        self.assertEqual(
            sanitize_account_name_for_snf("^startswithanillegalchar"),
            "_startswithanillegalchar",
        )
        self.assertEqual(
            len(
                sanitize_account_name_for_snf(
                    "ReallyLongAccountNameThatShouldBeTruncatedBecauseItsTooLong"
                )
            ),
            30,
        )


class FailureTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_event_parsing(self):
        sample_event = {}
        with self.assertRaises(ValueError) as _error:
            get_details_from_event(sample_event)
        self.assertEqual(
            str(_error.exception), "No S3 Event details present in event trigger"
        )
