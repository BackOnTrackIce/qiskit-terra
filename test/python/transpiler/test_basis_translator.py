from qiskit.compiler import transpile
from qiskit import  QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.providers.aer import QasmSimulator
from qiskit.circuit import ControlledGate
from qiskit.circuit import ParameterVector as _pv
import unittest
from qiskit.test import QiskitTestCase
from qiskit.providers.aer import QasmSimulator
from qiskit.circuit import SessionEquivalenceLibrary #equivalence_library
from qiskit.circuit import EquivalenceLibrary
from qiskit.extensions.standard import CXGate, ZGate
from qiskit.quantum_info import Operator


class Test_basis_translator(QiskitTestCase):
    """
    Tests to verify that consolidating blocks of gates into unitaries
    works correctly.
    """
    def test_new_gate_to_basis_translator(self):
        class TestGate(ControlledGate):

            def __init__(self):
                """Create new  gate."""
                super().__init__("testgate", 2, [], num_ctrl_qubits=1)


            def inverse(self):
                """Invert this gate."""
                return TestGate()

            def to_matrix(self):
                """Return a Numpy.array for the Cx gate."""
                return numpy.array([[1, 0, 0, 0],
                                    [0, 0, 0, 1],
                                    [0, 0, 1, 0],
                                    [0, 1, 0, 0]], dtype=complex)

        def tg(self, ctl, tgt):
            """Apply cu1 from ctl to tgt with angle theta."""
            return self.append(TestGate(), [ctl, tgt], [])


        # deifne a new decomposition
        qr= QuantumRegister(2, "q")
        qc = QuantumCircuit(qr)


        qc.cx(qr[0], qr[1])
        qc.z( qr[1])
        qc.cx(qr[0], qr[1])

        equivalencelibrary = EquivalenceLibrary()
        equivalencelibrary.add_equivalence(TestGate(), qc)

        QuantumCircuit.tg = tg

        backend = QasmSimulator()

        basis_gates = ['cx', 'z']
        qubits = 2
        q = QuantumRegister(qubits)
        c = ClassicalRegister(qubits)
        register = QuantumCircuit(q, c)

        register.tg(q[0], q[1])

        circuit = transpile(register,
                backend=backend,
                basis_gates=basis_gates, coupling_map=None, backend_properties=None,
                initial_layout=None, seed_transpiler=None,
                optimization_level=1,
                pass_manager=None, callback=None, output_name=None, equivalence_library=equivalencelibrary)

        resources_after = circuit.count_ops()
        self.assertEqual({'cx': 2, 'z': 1}, resources_after)





if __name__ == '__main__':
    unittest.main()