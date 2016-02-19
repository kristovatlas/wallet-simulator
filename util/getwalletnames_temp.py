import json
import urllib2
import ssl
from socket import error as SocketError
from sets import Set
import time

MAX_RETRY_TIME_IN_SEC = 2
NUM_SEC_TIMEOUT = 30
NUM_SEC_SLEEP = 0

API_KEY = 'kristov@openbitcoinprivacyproject.org'

def get_tx_info_url(tx_id):
        return ("https://www.walletexplorer.com/api/1/tx?txid=%s&caller=%s" %
            (tx_id, API_KEY))

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

def main():
    with open('block_398159_txids.json') as data_file:
        txids = json.load(data_file)['tx']
        print len(txids)
        unique_labels = Set()
        for txid in txids:
            print txid
            url = get_tx_info_url(txid)
            resp = fetch_url(url)
            json_obj = json.loads(resp)
            if json_obj['is_coinbase']:
                continue
            label = None
            try:
                label = json_obj['label']
            except KeyError:
                label = json_obj['wallet_id']
            print label
            unique_labels.add(label)
        print "----"
        for label in unique_labels:
            print label

def dprint(data):
    pass


if __name__ == '__main__':
    main()
