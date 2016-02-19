"""Convert any BTC float amount into satoshis as integer.

From https://en.bitcoin.it/wiki/Proper_Money_Handling_(JSON-RPC)
"""

def float_to_satoshis(value):
    return long(round(float(value) * 1e8))

def satoshis_to_float(amount):
    return float(int(amount) / 1e8)
