"""
Tests the account file processing lambda
"""
import unittest
from ..process_account_files import process_account, process_account_list, get_details_from_event


class SuccessTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_process_account_when_account_exists(self):
        test_account = {
            "alias": "MyCoolAlias",
            "account_full_name":"mytestaccountname",
        }
        account_lookup = {"mytestaccountname":1234567890}
        self.assertDictEqual(
            process_account(account_lookup, test_account),
            {
                "alias": "MyCoolAlias",
                "account_full_name":"mytestaccountname",
                "account_id": 1234567890,
                "needs_created": False,
            }
        )


    def test_process_account_when_account_doesnt_exist(self):
        test_account = {
            "alias": "MyCoolAlias",
            "account_full_name":"mytestaccountname",
        }
        account_lookup = {"mydifferentaccount":1234567890}
        self.assertDictEqual(
            process_account(account_lookup, test_account),
            {
                "alias": "MyCoolAlias",
                "account_full_name":"mytestaccountname",
                "needs_created": True,
            }
        )


    def test_process_account_list(self):
        all_accounts = [{"Name":"mytestaccountname", "Id":1234567890}]
        accounts_in_file = [
            {"account_full_name": "mytestaccountname"},
            {"account_full_name": "mynewaccountname"},
        ]
        self.assertListEqual(process_account_list(all_accounts, accounts_in_file), [
            {
                "account_full_name":"mytestaccountname",
                "needs_created": False,
                "account_id": 1234567890,
            },
            {
                "account_full_name":"mynewaccountname",
                "needs_created": True,
            }
        ])


class FailureTestCase(unittest.TestCase):
    # pylint: disable=W0106
    def test_event_parsing(self):
        sample_event = {}
        with self.assertRaises(ValueError) as _error:
            get_details_from_event(sample_event)
        self.assertEqual(
            str(_error.exception),
            "No S3 Event details present in event trigger"
        )
