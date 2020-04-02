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


"""Test the BasisTranslator pass"""

from numpy import pi

from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.transpiler.passes import SynthesizeUnitaries
from qiskit.circuit import EquivalenceLibrary
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.test import QiskitTestCase
from qiskit.quantum_info import Operator

class TestBasisTranslator(QiskitTestCase):
    """Test the BasisTranslator pass."""

    def test_definition_fallback(self):
        """Verify for gates without an equivalence we fall back to definition."""
        eq_lib = EquivalenceLibrary()

        qc = QuantumCircuit(1)
        qc.unitary([[0, 1], [1, 0]], [0])
        dag = circuit_to_dag(qc)

        expected = QuantumCircuit(1)
        expected.x(0)

        pass_ = SynthesizeUnitaries(eq_lib)
        actual = pass_.run(dag)

        self.assertTrue(Operator(dag_to_circuit(actual)).equiv(expected))

