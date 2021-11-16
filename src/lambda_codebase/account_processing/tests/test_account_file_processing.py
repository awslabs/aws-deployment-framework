"""
Tests the account file processing lambda
"""

from ..process_account_files import process_account, process_account_list

# pylint: disable=W0106
def test_process_account_when_account_exists():
    test_account = {"alias": "MyCoolAlias", "account_full_name":"mytestaccountname"}
    account_lookup = {"mytestaccountname":1234567890}
    assert process_account(account_lookup, test_account) == {"alias": "MyCoolAlias", "account_full_name":"mytestaccountname", "Id": 1234567890, "needs_created": False}

def test_process_account_when_account_doesnt_exist():
    test_account = {"alias": "MyCoolAlias", "account_full_name":"mytestaccountname"}
    account_lookup = {"mydifferentaccount":1234567890}
    assert process_account(account_lookup, test_account) == {"alias": "MyCoolAlias", "account_full_name":"mytestaccountname", "needs_created": True}

def test_process_account_list():
    all_accounts = [{"Name":"mytestaccountname", "Id":1234567890}]
    accounts_in_file = [{"account_full_name": "mytestaccountname"}, {"account_full_name": "mynewaccountname"}]
    assert process_account_list(all_accounts, accounts_in_file) == [
        {"account_full_name":"mytestaccountname", "needs_created": False, "Id": 1234567890},
        {"account_full_name":"mynewaccountname", "needs_created": True}
     ]
