"""Using cluster analysis, represents UTXO set of a wallet over time."""

from enum import IntEnum

import http #http.py
import bitcoind_rpc #bitcoind_rpc.py
from satoshi_convert import float_to_satoshis #satoshi_convert.py

ENABLE_DEBUG_PRINT = False

class TransactionType(IntEnum):
    RECEIVE = 1
    SEND = 2

class OutputNotFoundError(Exception):
    """Could not locate an output we were looking for in a previous tx."""
    pass

class CurrentTxNotSendError(Exception):
    """The currently iterated transaction is a receive tx, not a send tx."""
    pass

class CurrentTxIsLastError(Exception):
    """The currently iterated transaction is the last in this wallet."""
    pass

class Wallet(object):
    """Tracks approximate UTXO set of the wallet over time.

    A wallet in this context is a set of spendable UTXOs at a snapshot in time
    and is added to or subtracted from when a relevant transaction is created.

    Uses the WalletExplorer.com cluster analysis and bitcoind RPC interface.

    Attributes:
        iterate_until_send (bool): Determines whether next() will itereate one
            transaction at a time, or all transactions until just before a new
            send transaction is hit.
        wallet_label (str): The label designated for the wallet by the
            WalletExplorer.com API.
        txs (List): The 'txs' section of the JSON object returned by calling
            `json.loads` on WalletExplorer.com's API for /wallet.
        utxos (List): The current set of UTXOs for the wallet. Each UTXO is
            represented by a 3-tuple of (txid, output_index, amt_satoshis).
        tx_index (int): The current index of transactions as callers iterate
            through this object.
        conn (`RPCConnection`): A connetion object to the bitcoind RPC
            interface.

    Args:
        wallet_label (str): The name of the wallet you're iterating through.
        iterate_until_send (Optional[bool]): Determines whether next() will
            itereate one transaction at a time, or all transactions until just
            before a new send transaction is hit. Set to False by default.
        max_txs_download (Optional[int]): If set, only the specified number of
            transactions will be downloaded at most.

    Raises:
        http.WalletNotFoundError: Raised if not found at walletexplorer.com API.
        http.MaxTransactionsExceededError: Raised if the number of transactions
            in the wallet exceeds the specified `max_txs_download` param.
    """
    def __init__(self, wallet_label, iterate_until_send=False,
                 max_txs_download=None):
        assert isinstance(iterate_until_send, bool)
        assert max_txs_download is None or isinstance(max_txs_download, int)
        self.iterate_until_send = iterate_until_send
        self.wallet_label = wallet_label
        try:
            self.txs = http.get_all_wallet_txs(wallet_label,
                                               max_num_txs=max_txs_download)
        except http.WalletNotFoundError:
            raise
        except http.MaxTransactionsExceededError:
            raise
        dprint("Fetched %d transactions for %s" % (len(self.txs), wallet_label))
        self.utxos = []
        self.tx_index = 0 #incremented each time next_tx() is called
        self.conn = bitcoind_rpc.RPCConnection()
        self.max_txs_download = max_txs_download

    def get_num_txs(self):
        """Returns the number of transactions for this wallet as integer."""
        return len(self.txs)

    def get_inputs(self, txid):
        """Get a list of inputs for the specified transaction.

        Returns:
            List of utxos as tuples of (txid, output_index, amt_in_satoshis).
        """
        tx_rpc_json = self.conn.get_decoded_tx(txid)
        inputs = []
        for vin in tx_rpc_json['vin']:
            input_prev_txid = vin['txid']
            input_prev_index = vin['vout']
            input_rpc_json = self.conn.get_decoded_tx(input_prev_txid)
            input_amt = input_rpc_json['vout'][input_prev_index]['value']
            input_satoshis = float_to_satoshis(input_amt)
            utxo = (input_prev_txid,input_prev_index, input_satoshis)
            inputs.append(utxo)
        return inputs

    def get_utxos_mismatch_amt(self, txid, amt_list):
        """Return all utxos that don't match the output amounts specified.

        Args:
            txid (str): transaction hash
            amt_list (List[int]): List of amounts we want to omit, each
                expressed in integer satoshi terms.
        Returns:
            List of utxos as tuples of (txid, output_index, amt_in_satoshis).
        """
        assert type(txid) in (str, unicode)
        assert isinstance(amt_list, list)

        tx_rpc_json = self.conn.get_decoded_tx(txid)
        utxos = []
        for i, vout in enumerate(tx_rpc_json['vout']):
            output_val = float_to_satoshis(vout['value'])
            if output_val not in amt_list:
                utxo = (txid, i, output_val)
                utxos.append(utxo)
        return utxos

    def get_current_desired_spend(self):
        """Based on the current sending transaction, get the intended spend amt.

        Returns:
            int: The total desired spend implied by this sending transaction.
        """
        current_tx = self.txs[self.tx_index]
        if current_tx['type'] != 'sent':
            dprint(str(current_tx))
            raise CurrentTxNotSendError
        desired_spend = 0
        for output in current_tx['outputs']:
            desired_spend += float_to_satoshis(output['amount'])
        return desired_spend

    def get_utxos(self, txid, output_amt):
        """Find outputs for specified tx sent to this wallet.

        WalletExplorer.com's /wallet endpoint indicates a total amount sent
        to the wallet but not specifically which output(s). We'll first try
        to use bitcoind's RPC interface to match the amount to a unique
        transaction output. If that can't be done, we'll follow up with a call
        to the /tx API endpoint and get a complete list of outputs sent to the
        wallet.

        Args:
            txid (str): Transaction hash.
            output_amt (int): The amount of the output we want to find in
                integer satoshi terms. In the event of duplicate values in a
                transaction's outputs, the first one is used.

        Returns:
            List[utxos], with each utxo as a tuple of
                (txid, output_index, amt_satoshis).
        """
        dprint("Looking for output amt %s in %s" % (str(output_amt), txid))
        assert type(txid) in (str, unicode)
        assert isinstance(output_amt, int) or isinstance(output_amt, long)

        tx_rpc_json = self.conn.get_decoded_tx(txid)
        utxo = None
        for i, vout in enumerate(tx_rpc_json['vout']):
            if float_to_satoshis(vout['value']) == output_amt:
                if utxo is None:
                    utxo = (txid, i, output_amt)
                else:
                    #resolve ambiguity as to which output is correct
                    utxos = http.get_outputs_sent_to_wallet(txid,
                                                            self.wallet_label)
                    return utxos
        if utxo is None:
            #there may be multiple outputs that add up the specified amount
            utxos = http.get_outputs_sent_to_wallet(txid, self.wallet_label)
            utxo_sum = 0
            for utxo in utxos:
                utxo_sum += utxo[2]
            if utxo_sum != output_amt:
                raise OutputNotFoundError
            else:
                return utxos
        else:
            return [utxo]

    def is_next_tx_send(self):
        """Returns whether the next transaction to be iterated is a send.

        Raises:
            CurrentTxIsLastError: Raised if there are no remaining txs for this
                wallet.
        """
        if self.tx_index == len(self.txs):
            return False
        next_txn = self.txs[self.tx_index]
        return next_txn['type'] == 'sent'

    def next_tx(self):
        """Process the next transaction in this wallet.

        Returns:
            `TransactionType`: Whether the tx was a `SEND` or `RECEIVE`."""
        if self.tx_index == len(self.txs):
            raise StopIteration

        txn = self.txs[self.tx_index]

        self.tx_index += 1

        txid = txn['txid']
        if txn['type'] == 'received':
            amt = float_to_satoshis(txn['amount'])
            utxos = self.get_utxos(txid, amt)
            self.utxos.extend(utxos)
            return TransactionType.RECEIVE
        elif txn['type'] == 'sent':
            #remove inputs from utxos set
            inputs = self.get_inputs(txid)
            for tx_input in inputs:
                dprint(("Attempting to delete this utxo from set due to send: "
                        "%s") % str(tx_input))
                try:
                    self.utxos.remove(tx_input)
                except ValueError:
                    print(("WARNING: Missing input %s from wallet %s in tx %s. "
                           "This indicates a bug in this program, incomplete "
                           "clustering analysis, or a multi-party transaction "
                           "such as a CoinJoin. This input will be ignored.") %
                          (str(tx_input), self.wallet_label, txid))
                    continue
                dprint("Deleted this utxo from set due to send: %s" %
                       str(tx_input))

            #add change to utxo set, if any
            spend_amts = []
            for spend_output in txn['outputs']:
                assert spend_output['wallet_id'] != self.wallet_label
                spend_amt = float_to_satoshis(spend_output['amount'])
                spend_amts.append(spend_amt)
            change_utxos = self.get_utxos_mismatch_amt(txid, spend_amts)
            dprint("Adding these change utxos due to send: %s" %
                   str(change_utxos))
            self.utxos.extend(change_utxos)
            return TransactionType.SEND
        else:
            raise TypeError

    def __iter__(self):
        return self

    def next(self):
        """Iterate on the next transaction or transactions.

        Will process one tx if `iterate_until_send` is false, otherwise will
        continue until the next send transaction or the end of the transactions.
        """
        num_tx_processed_this_round = 0
        if not self.iterate_until_send:
            self.next_tx()
            return self.utxos
        while True:
            if self.is_next_tx_send() and num_tx_processed_this_round > 0:
                return self.utxos
            else:
                self.next_tx()
                num_tx_processed_this_round += 1

def dprint(msg):
    """Debug print statements."""
    if ENABLE_DEBUG_PRINT:
        print "DEBUG: %s" % msg
