"""Calcs % of txs from a WalletExplorer.com wallet could be BIP compliant.

https://github.com/OpenBitcoinPrivacyProject/rfc/blob/master/bips/obpp-03.mediawiki

A utxo is represented in this code as a 3-tuple of (txid, output_index, amt)
where txid is the transaction that created the ouput, output_index its order in
that tx's list of outputs, and amt is the satoshi integer amount.
"""
import json

from wallet import Wallet #wallet.py
import http #http.py
from . import core
from .core import NotEnoughFundsError

#If a wallet has more txs than this, skip it.
MAX_TXS_PER_WALLET = 100

MAX_NUM_WALLETS = None # Set to None to disable

FILE_JSON_LIST_OF_WALLET_IDS = 'data/block_398159_wallets.json'

ENABLE_DEBUG_PRINT = True

def test(wallet_id):
    """Tests standard and alternate forms using utxos from specified wallet.

    Args:
        wallet_id (str): ID assigned by WalletExplorer.com for specified wallet.

    Returns:
        (int, int, int, int): Number of transactions for this wallet that felt
            into various categories (both_sucess, standard_success,
            alternate_success, none_sucess)
    """
    num_both_success = 0
    num_standard_only = 0
    num_alternate_only = 0
    num_neither = 0
    try:
        test_wallet = Wallet(wallet_label=wallet_id, iterate_until_send=True,
                             max_txs_download=MAX_TXS_PER_WALLET)
    except http.WalletNotFoundError:
        print "Skipped %s because it's missing from API" % wallet_id
        return (0, 0, 0, 0)
    except http.MaxTransactionsExceededError:
        print "Skipped %s because it has too many txs" % wallet_id
        return (0, 0, 0, 0)
    for utxos in test_wallet:
        print "UTXOS=%s" % str(utxos)
        utxo_vals = sorted([utxo[2] for utxo in utxos], reverse=True)
        desired_spend = test_wallet.get_current_desired_spend()
        standard_success = True
        alternate_success = True
        try:
            core.simulate_standard_form(utxo_vals, desired_spend)
        except NotEnoughFundsError:
            standard_success = False

        try:
            core.simulate_alternate_form(utxo_vals, desired_spend)
        except NotEnoughFundsError:
            alternate_success = False

        if standard_success and alternate_success:
            num_both_success += 1
        if standard_success and not alternate_success:
            num_standard_only += 1
        if not standard_success and alternate_success:
            num_alternate_only += 1
        else:
            num_neither += 1

    return (num_both_success, num_standard_only, num_alternate_only, num_neither)

def main():
    """Determine number of spends from wallets involved in block 38159 could be
    BIP compliant.

    """
    num_both_success = 0
    num_standard_only = 0
    num_alternate_only = 0
    num_neither = 0
    try:
        with open(FILE_JSON_LIST_OF_WALLET_IDS) as json_file:
            wallet_ids = json.load(json_file)
            for i, wallet_id in enumerate(wallet_ids):
                if i == MAX_NUM_WALLETS:
                    break

                print "Evaluating compatibility for wallet %s..." % wallet_id
                results = test(wallet_id)
                num_both_success += results[0]
                num_standard_only += results[1]
                num_alternate_only += results[2]
                num_neither += results[3]

                print(("Stats: Total txs standard & alternate compliant: %d; "
                       "standard only: %d; alternate only: %d; neither: %d") %
                      (num_both_success, num_standard_only, num_alternate_only,
                       num_neither))
    except Exception as err:
        print "Encountered unhandled exception: %s" % str(err)
    finally:
        print(("Stats: Total txs standard & alternate compliant: %d; standard "
               "only: %d; alternate only: %d; neither: %d") %
              (num_both_success, num_standard_only, num_alternate_only,
               num_neither))
        print "All wallets completed."

if __name__ == "__main__":
    main()
