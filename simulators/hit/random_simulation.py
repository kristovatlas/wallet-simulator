"""Simulates the attempt to comply with the BIP using random wallet UTXOs."""

from random import randint

from . import core
from .core import NotEnoughFundsError
from .core import dprint

MAX_UTXOS = 10

MIN_VALUE = 1
MAX_VALUE = 10

NUM_TESTS = 10000

def generate_utxos():
    """Returns: List of utxo values as integers."""
    num_utxos = randint(1, MAX_UTXOS)
    utxos = []
    for _ in range(0, num_utxos):
        utxos.append(randint(MIN_VALUE, MAX_VALUE))
    return utxos

def generate_desired_spend(sum_avail_utxos):
    """Generate a random desired spend betwen 1 and the wallet balance."""
    return randint(1, sum_avail_utxos)

def test():
    """Tests standard and alternate form using wallet with random utxos.

    Returns:
        (bool, bool): (standard_success, alternate_success)
    """
    standard_success = True
    alternate_success = True

    available_utxos = sorted(generate_utxos(), reverse=True)
    print "Available UTXOs: %s sum=%d" % (str(available_utxos),
                                          sum(available_utxos))
    sum_avail_utxos = sum(available_utxos)

    desired_spend = generate_desired_spend(sum_avail_utxos)
    print "Desired Spend: %d" % desired_spend

    dprint("Attempting standard form...")
    try:
        core.simulate_standard_form(available_utxos, desired_spend)
    except NotEnoughFundsError:
        standard_success = False
        print "Not enough funds for standard form."

    dprint("Attempting alternate form...")
    try:
        core.simulate_alternate_form(available_utxos, desired_spend)
    except NotEnoughFundsError:
        alternate_success = False
        print "Not enough funds for alternate form."

    return (standard_success, alternate_success)

def main():
    """Run a bunch of tests."""
    num_standard_only = 0
    num_alternate_only = 0
    num_both = 0
    num_neither = 0

    for i in range(0, NUM_TESTS):
        dprint("Beginning test %d of %d" % (i + 1, NUM_TESTS))
        standard_success, alternate_success = test()
        if standard_success and not alternate_success:
            num_standard_only += 1
        elif not standard_success and alternate_success:
            num_alternate_only += 1
        elif standard_success and alternate_success:
            num_both += 1
        else:
            num_neither += 1

    print(("In %d tests: %d compatible with both, %d standard only, %d "
           "alternate only, %d neither.") %
          (NUM_TESTS, num_both, num_standard_only, num_alternate_only,
           num_neither))

if __name__ == "__main__":
    main()
