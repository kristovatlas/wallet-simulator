"""Takes care of fetching data via HTTP."""
import urllib2
import ssl
from socket import error as SocketError
import json
import time

from satoshi_convert import float_to_satoshis #satoshi_convert.py

ENABLE_DEBUG_PRINT = False

WE_FETCH_WALLET_TX_BASE = "https://www.walletexplorer.com/api/1/wallet"
WE_FETCH_TX_BASE = "https://www.walletexplorer.com/api/1/tx"
API_KEY = "wallet-simulator"

#Currently WalletExplorer.com only permits fetching 100 transactions at a time.
NUM_TX_PER_FETCH = 100

MAX_RETRY_TIME_IN_SEC = 2
NUM_SEC_TIMEOUT = 30
NUM_SEC_SLEEP = 0

class WalletNotFoundError(Exception):
    """Wallet not found at WalletExplorer.com"""
    pass

class MaxTransactionsExceededError(Exception):
    """Wallet contains more transactions than permissible."""
    pass

def fetch_url(url):
    """Fetch contents of remote page as string for specified url."""

    if NUM_SEC_SLEEP > 0:
        time.sleep(NUM_SEC_SLEEP)

    current_retry_time_in_sec = 0

    dprint("Fetching url: %s" % url)

    response = ''
    while current_retry_time_in_sec <= MAX_RETRY_TIME_IN_SEC:
        if current_retry_time_in_sec:
            time.sleep(current_retry_time_in_sec)
        try:
            response = urllib2.urlopen(url=url, timeout=NUM_SEC_TIMEOUT).read()
            if response is None:
                #For some reason, no handler handled the request
                raise Exception
            return response
        except (urllib2.HTTPError, ssl.SSLError) as err:
            #There was a problem fetching the page, maybe something other than
            #   HTTP 200 OK.
            if current_retry_time_in_sec == MAX_RETRY_TIME_IN_SEC:
                raise Exception
            else:
                current_retry_time_in_sec = current_retry_time_in_sec + 1
                dprint(("Encountered HTTPError fetching '%s'. Will waiting for "
                        "%d seconds before retrying. Error was: '%s'") %
                       (url, current_retry_time_in_sec, str(err)))
        except urllib2.URLError as err:
            if current_retry_time_in_sec == MAX_RETRY_TIME_IN_SEC:
                raise Exception
            else:
                current_retry_time_in_sec = current_retry_time_in_sec + 1
                dprint(("Encountered URLError fetching '%s'. Will waiting for "
                        "%d seconds before retrying. Error was: '%s'") %
                       (url, current_retry_time_in_sec, str(err)))
        except SocketError as err:
            if current_retry_time_in_sec == MAX_RETRY_TIME_IN_SEC:
                raise Exception
            else:
                current_retry_time_in_sec = current_retry_time_in_sec + 1
                dprint(("Encountered SocketErr fetching '%s'. Will waiting for "
                        "%d seconds before retrying. Error was: '%s'") %
                       (url, current_retry_time_in_sec, str(err)))

def get_num_txs(wallet_label):
    """Get the number of transactions present in this wallet.

    Raises:
        WalletNotFoundError: If wallet not found at walletexplorer.com.
    """
    url = get_wallet_txs_offsets_url(wallet_label, 0)
    dprint(url)
    wallet_json = json.loads(fetch_url(url))
    try:
        if not wallet_json['found']:
            raise WalletNotFoundError
        return wallet_json['txs_count']
    except KeyError:
        raise WalletNotFoundError

def get_wallet_txs_offsets_url(wallet_label, offset):
    """Returns URL for fetching a wallet's transactions."""
    return ("%s?wallet=%s&from=%d&count=%d&caller=%s" %
            (WE_FETCH_WALLET_TX_BASE, wallet_label, offset, NUM_TX_PER_FETCH,
             API_KEY))

def get_tx_data_url(txid):
    """Returns URL for fetching data about a transaction."""
    return "%s?txid=%s&caller=%s" % (WE_FETCH_TX_BASE, txid, API_KEY)

def get_all_wallet_txids(wallet_label):
    """Get a list of transaction IDs belonging to the specified wallet.

    Wallet IDs will be listed in chronological order, with the earliest being
    in the 0th position.

    Raises:
        WalletNotFoundError: If wallet not found at walletexplorer.com.
    """
    num_txs = get_num_txs(wallet_label)
    txids = []
    for offset in range(0, num_txs, NUM_TX_PER_FETCH):
        url = get_wallet_txs_offsets_url(wallet_label, offset)
        json_obj = json.loads(fetch_url(url))
        if not json_obj['found']:
            raise WalletNotFoundError
        try:
            for txn in json_obj['txs']:
                txids.insert(0, txn['txid'])
        except KeyError:
            raise WalletNotFoundError
    return txids

def get_tx_data_json(txid):
    """Fetch WalletExplorer.com's TX data for specified tx."""
    url = get_tx_data_url(txid)
    json_obj = json.loads(fetch_url(url))
    assert json_obj['found']
    return json_obj

def get_outputs_sent_to_wallet(txid, wallet_label):
    """Find all outputs in tx sent to specified wallet using remote API.

    Returns:
        List[utxos], with each tuple as (txid, output_index, amt_satoshis)
    """
    tx_json = get_tx_data_json(txid)
    utxos = []
    for i, output in enumerate(tx_json['out']):
        receiver_wallet = None
        amt_in_satoshis = float_to_satoshis(output['amount'])
        if 'label' in output:
            receiver_wallet = output['label']
        else:
            receiver_wallet = output['wallet_id']
        if receiver_wallet == wallet_label:
            utxo = (txid, i, amt_in_satoshis)
            utxos.append(utxo)
    return utxos

def get_all_wallet_txs(wallet_label, max_num_txs=None):
    """Get a list of transaction objects belonging to specified wallet.

    Each object contains these fields:
        * txid
        * block_height
        * block_pos
        * time
        * balance (in BTC)
        * type (received|sent)
        * wallet_id (if received)
        * amount (if received)
        * label (if received)
        * fee (if sent)
        * outputs (list, if sent)
            * per output:
                * amount
                * wallet_id

    Transactions will be listed in chronological order, with the earliest being
    in the 0th position.

    Args:
        wallet_label (str): The wallet label assigned by walletexplorer.com
        max_num_txs (Optional[int]): The maximum number of transactions we
            expect to see in the wallet. If there are more than this, an error
            is raised. This can prevent the function from downloading very large
            wallets.
    Raises:
        MaxTransactionsExceededError: Raised if the number of transactions for
            the specified wallet exceeds the optional `max_num_txs` param.
    """
    assert max_num_txs is None or isinstance(max_num_txs, int)
    num_txs = get_num_txs(wallet_label)
    if max_num_txs is not None and num_txs > max_num_txs:
        raise MaxTransactionsExceededError
    txs = []
    for offset in range(0, num_txs, NUM_TX_PER_FETCH):
        url = get_wallet_txs_offsets_url(wallet_label, offset)
        json_obj = json.loads(fetch_url(url))
        dprint('Fetched %d txs for %s' % (len(json_obj['txs']), wallet_label))
        txs.extend(json_obj['txs'])
        dprint("New length of txs array is %d" % len(txs))
    txs.reverse()
    return txs

def dprint(msg):
    """Debug print statements."""
    if ENABLE_DEBUG_PRINT:
        print "DEBUG: %s" % msg
