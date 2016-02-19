"""Unit tests for `wallet` module that requires network traffic."""

import unittest
import wallet #wallet.py
import http #http.py

class WalletTest(unittest.TestCase):
    """Slow tests for the `wallet` module."""

    def test_utxo_enumeration(self):
        """Load wallet with a bunch of txs and check some of the snapshots."""
        for i, utxos in enumerate(wallet.Wallet('MineField.BitcoinLab.org')):
            if i==0:
                self.assertEqual(len(utxos), 1)
                txid = utxos[0][0]
                output_index = utxos[0][1]
                amt_satoshis = utxos[0][2]
                self.assertEqual(txid,
                                 ('8f3fbb758556b8fbe99d5cf6ab19707d42524a7a839b'
                                  '08d19adf34153a38d369'))
                self.assertEqual(output_index, 0)
                self.assertEqual(amt_satoshis, 25500)
            if i==10:
                #this transaction has an input with a value that would match
                #multiple outputs in the previous tx. This must be correctly
                #resolved with an additional call to the /tx API endpoint.
                txid = utxos[10][0]
                output_index = utxos[10][1]
                amt_satoshis = utxos[10][2]
                self.assertEqual(
                    txid,
                    ('500b5af07919e9693c4124c4ba4fba68a991487c40f1e116b64fed31e'
                     'bd303ee'))
                self.assertEqual(output_index, 14)
                self.assertEqual(amt_satoshis, 10000)
            if i==24:
                #first send transaction, has no change outputs only 2 sends
                #after 24 receives, 19 utxos are shed as inputs
                self.assertEqual(len(utxos), 5)
                self.assertEqual(
                    utxos[0][0],
                    ('b8d8a24adc428d1d8c54d2f57f68d2dcf393465de1e201ef81900beb6'
                     'db5e8dc'))
                self.assertEqual(utxos[0][1], 0)
                self.assertEqual(utxos[0][2], 3000000)

                self.assertEqual(
                    utxos[1][0],
                    ('4a0acc2be3761b575b5b9ad82bec6b81bf519609bcfeb1eef624a98ea'
                     '564a854'))
                self.assertEqual(utxos[1][1], 0)
                self.assertEqual(utxos[1][2], 3700000)

                self.assertEqual(
                    utxos[2][0],
                    ('500b5af07919e9693c4124c4ba4fba68a991487c40f1e116b64fed31e'
                     'bd303ee'))
                self.assertEqual(utxos[2][1], 14)
                self.assertEqual(utxos[2][2], 10000)

                self.assertEqual(
                    utxos[3][0],
                    ('010f833ec2bbcfc8d492fb4dc8a1b25c711b374f488161002d20bd719'
                     '02fe523'))
                self.assertEqual(utxos[3][1], 0)
                self.assertEqual(utxos[3][2], 200000)

                self.assertEqual(
                    utxos[4][0],
                    ('0b596a8c22693d727931850225ffddb48d9953e7472a167475de87bed'
                     '0068677'))
                self.assertEqual(utxos[4][1], 3)
                self.assertEqual(utxos[4][2], 10000)
            if i==25:
                break

    def test_iterate_until_send(self):
        """This should iterate until just before it hits a send transaction."""
        for i, utxos in enumerate(wallet.Wallet('MineField.BitcoinLab.org',
                                                iterate_until_send=True)):
            if i==0:
                #just before first send transaction, after 24 receives
                self.assertEqual(len(utxos), 24)
                self.assertEqual(
                    utxos[0][0],
                    ('8f3fbb758556b8fbe99d5cf6ab19707d42524a7a839b08d19adf34153'
                     'a38d369'))
                self.assertEqual(utxos[0][1], 0)
                self.assertEqual(utxos[0][2], 25500)

                self.assertEqual(
                    utxos[23][0],
                    ('0b596a8c22693d727931850225ffddb48d9953e7472a167475de87bed'
                     '0068677'))
                self.assertEqual(utxos[23][1], 3)
                self.assertEqual(utxos[23][2], 10000)

                break

    def test_get_current_desired_spend(self):
        """Confirm that desired spend works correctly."""
        test_wallet = wallet.Wallet('MineField.BitcoinLab.org',
                                    iterate_until_send=True)
        for i, utxos in enumerate(test_wallet):
            if i==0:
                #first send transaction, has no change outputs only 2 sends
                #after 24 receives, 19 utxos are shed as inputs
                #spend = 0.01000001 BTC + 0.1365 BTC = 14650001 satoshis
                desired_spend = test_wallet.get_current_desired_spend()
                self.assertEqual(desired_spend, 14650001)
            if i==1:
                #second send transaction, spend = 0.1 BTC
                desired_spend = test_wallet.get_current_desired_spend()
                self.assertEqual(desired_spend, 10000000)
                break

    def test_max_txs_download(self):
        """Confirm that huge wallets aren't downloaded."""
        with self.assertRaises(http.MaxTransactionsExceededError):
            test_wallet = wallet.Wallet('MineField.BitcoinLab.org',
                                    max_txs_download=100)

    def test_apparent_coinjoin(self):
        """Test that no exception is thrown for wallet that has a CoinJoin."""
        test_wallet = wallet.Wallet('923197ea09681d34', iterate_until_send=True)
        for utxos in enumerate(test_wallet):
            pass

unittest.TestLoader().loadTestsFromTestCase(WalletTest)
