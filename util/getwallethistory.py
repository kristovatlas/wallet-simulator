import http #http.py

txs = http.get_all_wallet_txs('MineField.BitcoinLab.org')
for i, txn in enumerate(txs):
    print "%i: %s" % (i, str(txn))
