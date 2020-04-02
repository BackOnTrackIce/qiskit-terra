# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Translates gates to a target basis using a given equivalence library."""

from qiskit.dagcircuit import DAGCircuit
from qiskit.exceptions import QiskitError
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.basis import Unroller

class SynthesizeUnitaries(TransformationPass):
    """Foo"""

    def __init__(self, equivalence_library):
        """Bar"""
        super().__init__()
        self._equiv_lib = equivalence_library

    def run(self, dag):
        """
        """
        for node in dag.op_nodes():
            if self._equiv_lib.has_entry(node.op):
                continue

            try:
                rule = node.op.definition
            except TypeError as err:
                raise QiskitError('Error decomposing node {}: {}'.format(node.name, err))


            if not rule:
                continue
            # hacky way to build a dag on the same register as the rule is defined
            # TODO: need anonymous rules to address wires by index
            decomposition = DAGCircuit()
            qregs = {qb.register for inst in rule for qb in inst[1]}
            cregs = {cb.register for inst in rule for cb in inst[2]}
            for qreg in qregs:
                decomposition.add_qreg(qreg)
            for creg in cregs:
                decomposition.add_creg(creg)
            for inst in rule:
                decomposition.apply_operation_back(*inst)

            unrolled_dag = Unroller(['u3', 'cx']).run(decomposition)
            dag.substitute_node_with_dag(node, unrolled_dag)

        return dag
