"""Fetches data from bitcoind's RPC interface."""
import ConfigParser
from bitcoinrpc.authproxy import AuthServiceProxy

CONFIG_FILENAME = 'app.cfg'

class RPCConnection(object):
    """Creates a continuous connection to the bitcoind RPC interface.

    RPC connections are configured by the configuration file referred to by
    `CONFIG_FILENAME`.

    Attributes:
        conn (`AuthServiceProxy`): A connection to the RPC interface.
    """
    def __init__(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(CONFIG_FILENAME)
        username = config_parser.get(section='RPC', option='rpc_username')
        password = config_parser.get(section='RPC', option='rpc_password')
        host = config_parser.get(section='RPC', option='rpc_host')
        port = config_parser.get(section='RPC', option='rpc_port')

        self.conn = AuthServiceProxy("http://%s:%s@%s:%s" %
                                     (username, password, host, port))

    def get_block_hash_at_height(self, block_height):
        """Get the hash of the block at the specified block height."""
        return self.conn.getblockhash(block_height)

    def get_json_for_block_hash(self, block_hash):
        """Get a JSON represntation of the specified block."""
        return self.conn.getblock(block_hash)

    def get_tx_ids_at_height(self, block_height):
        """Get a list of transaction IDs contained in the specified block."""
        block_hash = self.get_block_hash_at_height(block_height)
        tx_json = self.get_json_for_block_hash(block_hash)
        tx_ids = []
        for tx_id in tx_json['tx']:
            tx_ids.append(tx_id)
        return tx_ids

    def get_raw_tx(self, tx_id):
        """Return transaction in raw format.

        If the requested transaction is the sole transaction of the genesis
        block, bitcoind's RPC interface will throw an error 'No information
        available about transaction (code -5)' so we preempt this by raising a
        custom error that callers should handle; iterating callers should just
        move onto the next tx.
        """
        if tx_id == ('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7af'
                     'deda33b'):
            raise IndexError
        else:
            return self.conn.getrawtransaction(tx_id)

    def get_decoded_tx(self, tx_id):
        """Gets the transaction in JSON format from the RPC interface."""
        try:
            return self.conn.decoderawtransaction(self.get_raw_tx(tx_id))
        except IndexError:
            #bitcoind won't generate this, but here's what it would look like
            genesis_json = {
                'txid':    ('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2'
                            '127b7afdeda33b'),
                'version':  1,
                'locktime': 0,
                'vin': [{
                    "sequence":4294967295,
                    'coinbase': ('04ffff001d0104455468652054696d65732030332f4a6'
                                 '16e2f32303039204368616e63656c6c6f72206f6e2062'
                                 '72696e6b206f66207365636f6e64206261696c6f75742'
                                 '0666f722062616e6b73')
                }],
                'vout': [
                    {
                        'value': 50.00000000,
                        'n': 0,
                        'scriptPubKey': {
                            'asm': ('04678afdb0fe5548271967f1a67130b7105cd6a828'
                                    'e03909a67962e0ea1f61deb649f6bc3f4cef38c4f3'
                                    '5504e51ec112de5c384df7ba0b8d578a4c702b6bf1'
                                    '1d5f OP_CHECKSIG'),
                            'hex': ('4104678afdb0fe5548271967f1a67130b7105cd6a8'
                                    '28e03909a67962e0ea1f61deb649f6bc3f4cef38c4'
                                    'f35504e51ec112de5c384df7ba0b8d578a4c702b6b'
                                    'f11d5fac'),
                            'reqSigs': 1,
                            'type': 'pubkey',
                            'addresses': ['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']
                        }
                    }
                ]
            }
            return genesis_json
