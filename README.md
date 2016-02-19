# wallet-simulator

Uses clustering analysis of addresses/transactions on the Bitcoin blockchain to approximate the UTXO set of wallets, as well as desired spend values at the time of outgoing payments. Using this data, an alternate history of transactions can be simulated.

Clustering anayalsis is provided by the WalletExplorer.com API.

## Usage

```python

for utxos in Wallet(wallet_label=wallet_id):
    #do something with utxos
```

To see an example of usage of the `Wallet` class, the `print` module. You can execute that module as follows:

```
$cd wallet-simluator
$python -m simulators.print 3562f0c16b41b2f9
```

## Simulations

Modules that make use of the wallet simulation functionality reside in the `simulators` directory. These currently include:

* `print` -- a simple example of how to use the `wallet` module.
* `hit` -- module containing simulations related to Heterogeneous Input Transactions
  * `random_simulation` -- generates some random bitcoin values for a hypothetical wallet and tests HIT compliance
  * `wallet_simulation` -- uses the `wallet` module to test HIT compliance with real wallets

### Running HIT Simulations

`python -m simulators.hit.random_simulation`

`python -m simulators.hit.wallet_simulation`

## Requirements

Tested with Python 2.7.

This code base uses the bitcoind-style RPC interface to query basic information about Bitcoin transactions. To configure connection to this interface, create an `app.cfg` as follows:

```INI
[RPC]
rpc_username=my_username #replace as appropriate
rpc_password=my_password #replace as appropriate
rpc_host=127.0.0.1 #replace as appropriate
rpc_port=8332 #replace as appropriate

```

## Primary Authors

Kristov Atlas <firstname @ openbitcoinprivacyproject.org>
