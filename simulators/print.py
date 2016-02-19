"""Prints the UTXO set and desired spend for each outgoing transaction.

"""

import sys

import http #http.py
from wallet import Wallet #wallet.py

def main():
    try:
        wallet_id = sys.argv[1]
        sample_wallet = None
        try:
            sample_wallet = Wallet(wallet_label=wallet_id,
                                   iterate_until_send=True)
        except http.WalletNotFoundError:
            print "Couldn't find that wallet."
            sys.exit()
        for utxos in sample_wallet:
            print "UTXOs: %s" % str(utxos)
            print("Desired Spend (in satoshis): %d" %
                  sample_wallet.get_current_desired_spend())

    except Exception as err:
        print "Error: %s" % str(err)
        print "Usage: print.py 3562f0c16b41b2f9"

if __name__ == '__main__':
    main()
