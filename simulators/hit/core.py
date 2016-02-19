# -*- coding: utf-8 -*-

"""Contains core logic for testing Heterogenous Input Transcactions.

A draft form of the BIP can be found here:
https://github.com/OpenBitcoinPrivacyProject/rfc/blob/master/bips/obpp-03.mediawiki
"""

import copy
import math

ENABLE_DEBUG_PRINT = False

#Don't try more than this many attempts for standard form transactions
MAX_STANDARD_FORM_ATTEMPTS = 1000 #Set to None to disable

class NotEnoughFundsError(Exception):
    """Not enough funds to match HIT form."""
    pass

def simulate_standard_form(availabile_utxo_vals, desired_spend):
    """Determines whether standard form is possible based on utxos and spend.

    Raises:
        NotEnoughFundsError: If there are not enough funds to match the standard
            form.
    """
    if len(availabile_utxo_vals) <= 1:
        print 'Not enough funds for standard form for this transaction.'
        raise NotEnoughFundsError
    if sum(availabile_utxo_vals) < desired_spend * 2:
        print 'Not enough funds for standard form for this transaction.'
        raise NotEnoughFundsError

    solution_found = False
    max_amt_to_double = sum(availabile_utxo_vals) / 2
    step = 1
    if MAX_STANDARD_FORM_ATTEMPTS is not None:
        step = int(math.ceil((max_amt_to_double - desired_spend + 1) * 1.0 /
                             MAX_STANDARD_FORM_ATTEMPTS))
    for amt_to_double in range(desired_spend, max_amt_to_double + 1, step):
        required_outputs = [amt_to_double, amt_to_double]
        try:
            match_standard_form(availabile_utxo_vals,
                                required_outputs=required_outputs)
            solution_found = True
            break
        except NotEnoughFundsError:
            pass
    if not solution_found:
        print 'Not enough funds for standard form for this transaction.'
        raise NotEnoughFundsError

def match_standard_form(available_utxo_vals, required_outputs=None):
    """Tries to match standard form using outputs that MUST appear in the tx.

    This is not an optimized algorithm, nor a complete one when searching for
    matches. In general, it follows the rule that we will greedily add
    the largest unused utxo value in the wallet to the inputs to balance
    between the inputs and outputs, but defer adding outputs unless we have an
    excellent idea about which outputs we want to try adding.

    Args:
        available_utxo_vals (List[int]): UTXOs available for inclusion as
            inputs.
        required_outputs (Optional[List[int]]): Values that must be included in
            the outputs, e.g. as the user's desired spend.
    Raises:
        NotEnoughFundsError: If there are not enough funds to match the standard
            form.
    """
    if required_outputs is None:
        required_outputs = []

    dprint("Attempting standard form with required outputs %s" %
           str(required_outputs))

    if sum(available_utxo_vals) < sum(required_outputs):
        raise NotEnoughFundsError
    remaining_utxos = sorted(copy.copy(available_utxo_vals), reverse=True)
    inputs = []
    outputs = []
    for required_output in required_outputs:
        outputs.append(required_output)

    #balance number of inputs and outputs
    while len(inputs) != len(outputs) or sum(inputs) != sum(outputs):
        #add inputs to account for all required outputs
        balance_outputs_with_new_inputs(remaining_utxos, inputs, outputs)

        #sum(inputs) >= sum(outputs) and len(inputs) >= len(outputs)
        if len(inputs) == len(outputs) and sum(inputs) == sum(outputs):
            break

        elif len(inputs) == len(outputs) and sum(inputs) > sum(outputs):
            #try to balance by adding an input and iterating again
            add_largest_input(remaining_utxos, inputs)

        elif len(inputs) > len(outputs) and sum(inputs) == sum(outputs):
            #can't balance by adding additional outputs, try adding input
            add_largest_input(remaining_utxos, inputs)

        elif len(inputs) > len(outputs) and sum(inputs) > sum(outputs):
            difference = sum(inputs) - sum(outputs)
            outputs_max = max(outputs)
            num_outputs_missing = len(inputs) - len(outputs)
            if num_outputs_missing == 1:
                #only room for one change output
                if difference > outputs_max and difference not in outputs:
                    #adding the difference as change would break Standard Form
                    #rule 4. try adding an input and see if that shakes things
                    #up.
                    add_largest_input(remaining_utxos, inputs)
                else:
                    #add one more change output and we should be good to go!
                    outputs.append(difference)
            else:
                #room for multiple change outputs, so try adding change_outputs
                #until balanced
                if difference >= num_outputs_missing:
                    attempted_change = break_into_parts(
                        difference, num_outputs_missing)
                    attempted_outputs = outputs + attempted_change
                    new_max = max(attempted_outputs)
                    if attempted_outputs.count(new_max) >= 2:
                        #compatible!
                        outputs = attempted_outputs
                    else:
                        #this would have broken Standard Fork rule 4.
                        if difference >= outputs_max:
                            outputs.append(outputs_max)
                        else:
                            outputs.append(difference)
                else:
                    #can't break outputs into smaller than 1 satoshi
                    add_largest_input(remaining_utxos, inputs)
        else:
            raise ValueError(('Condition should be unreachable with inputs=%s '
                              'and outputs=%s') % (str(inputs), str(outputs)))

    print_tx(form="standard", inputs=inputs, outputs=outputs)

def add_largest_input(remaining_utxos, inputs):
    """Add the largest utxo value in the remaining set to the inputs.

    Args:
        remaining_utxos (List[int]): A reverse sorted list of utxos values in
            the wallet not yet assigned to inputs for the current tx.
        inputs (List[int]): A list of inputs for the transaction.
    """
    if len(remaining_utxos) == 0:
        raise NotEnoughFundsError
    inputs.append(remaining_utxos.pop(0))

def balance_outputs_with_new_inputs(remaining_utxos, inputs, outputs):
    """Add inputs until they balance out or overtake the outputs."""
    while sum(inputs) < sum(outputs) or len(inputs) < len(outputs):
        add_largest_input(remaining_utxos, inputs)

def print_tx(form, inputs, outputs):
    """Print details about the transaction.

    Args:
        form (str): Standard form or alternate form.
        inputs (List[int]): Input values
        outputs (List[int]): Output values
    """
    print "Transaction: %s form" % form
    print "\tInputs:"
    for tx_input in inputs:
        print "\t\t%d" % tx_input
    print "\tOutputs:"
    for tx_output in outputs:
        print "\t\t%d" % tx_output

def break_into_parts(int_val, num_parts):
    """Creates a list of integers that add up to the specified value."""
    assert isinstance(int_val, int) or isinstance(int_val, long)
    assert isinstance(num_parts, int)
    assert int_val >= num_parts

    parts = []
    for _ in range(0, num_parts - 1):
        val = int(int_val / num_parts)
        if val == 0:
            val = 1
        parts.append(val)
    parts.append(int_val - sum(parts))
    return parts

def alternate_form_round(avail_utxo_vals, inputs, outputs, desired_spend):
    """Attempts to create an alternate form HIT using current wallet state.

    Args:
        avail_utxo_vals (List[int]): UTXO values available for spending in the
            simulated transaction.
        inputs (List[int]): List of UTXOs already allocated to the transaction,
            previously taken from the `available_utxo_vals`.
        outputs (List[int]): Output values assigned to the transaction.
        desired_spend (int): The amount that the user wants to send in the
            simulated transaction, and which must appear at least once in the
            outputs by the end of this process.
    """
    round_inputs = []
    #Find the smallest combination of inputs whose value is at least the value
    #   of the desired spend
    if sum(avail_utxo_vals) < desired_spend:
        raise NotEnoughFundsError

    while sum(round_inputs) < desired_spend:
        round_inputs.append(avail_utxo_vals.pop(0))

    inputs += round_inputs

    #Add a spend output to the transaction.
    outputs.append(desired_spend)

    #Add a change output to the transaction containing the difference between
    #   the current set of inputs and the desired spend.
    change = sum(round_inputs) - desired_spend
    if change > 0:
        outputs.append(change)

def simulate_alternate_form(avail_utxo_vals, desired_spend):
    """Determines whether alternate form is possible based on utxos and spend.

    Raises:
        NotEnoughFundsError: If there are not enough funds to match the
        alternate form.

    """
    inputs = []
    outputs = []

    if desired_spend * 2 > sum(avail_utxo_vals):
        print "Not enough funds for alternative form for this transaction."
        raise NotEnoughFundsError

    #round 1
    try:
        alternate_form_round(avail_utxo_vals, inputs, outputs, desired_spend)
    except NotEnoughFundsError:
        print "Not enough funds for alternative form for this transaction."
        raise

    #Repeat step 1 to create a second spend output and change output.
    try:
        alternate_form_round(avail_utxo_vals, inputs, outputs, desired_spend)
    except NotEnoughFundsError:
        print "Not enough funds for alternative form for this transaction."
        raise

    print_tx(form="alternate", inputs=inputs, outputs=outputs)

def dprint(data):
    """Print debug information, if flag is set to True."""
    if ENABLE_DEBUG_PRINT:
        print "%s" % str(data)
