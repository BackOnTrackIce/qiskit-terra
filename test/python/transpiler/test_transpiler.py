from qiskit.compiler import transpile
from qiskit import  QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.providers.aer import QasmSimulator
from qiskit.circuit import ControlledGate
from qiskit.circuit import ParameterVector as _pv
import unittest
from qiskit.test import QiskitTestCase
from qiskit.providers.aer import QasmSimulator
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary #equivalence_library
from qiskit.circuit import EquivalenceLibrary

class Test_transpiler(QiskitTestCase):
    """
    Tests to verify that consolidating blocks of gates into unitaries
    works correctly.
    """
    def test_different_equivalenceLibraries(self):
        class TestGate(ControlledGate):
            """controlled-u1 gate."""

            def __init__(self, theta):
                """Create new cu1 gate."""
                super().__init__("cxy", 2, [theta], num_ctrl_qubits=1)
                # self.base_gate = YGate
                # self.base_gate_name = "x"

            def inverse(self):
                """Invert this gate."""
                return TestGate(-self.params[0])

            def to_matrix(self):
                """Return a Numpy.array for the Cx gate."""
                return numpy.array([[1, 0, 0, 0],
                                    [0, 0, 0, 1],
                                    [0, 0, 1, 0],
                                    [0, 1, 0, 0]], dtype=complex)

        def tg(self, theta, ctl, tgt):
            """Apply cu1 from ctl to tgt with angle theta."""
            return self.append(TestGate(theta), [ctl, tgt], [])


        # deifne a new decomposition
        qr= QuantumRegister(2, "q")
        qc = QuantumCircuit(qr)
        n_params = 1
        th = _pv('th', n_params)
        qc.cx(qr[0], qr[1])
        qc.u1(th[0], [qr[0]])
        qc.cx(qr[0], qr[1])

        equivalencelibrary = EquivalenceLibrary()
        equivalencelibrary.add_equivalence(TestGate(*th), qc)

        qr_2 = QuantumRegister(2, "q")
        qc_2 = QuantumCircuit(qr_2)
        n_params_2 = 1
        th_2 = _pv('th', n_params)
        qc_2.cz(qr_2[0], qr_2[1])
        qc_2.u1(th_2[0], [qr_2[0]])
        qc_2.cz(qr_2[0], qr_2[1])


        equivalencelibrary2 = EquivalenceLibrary()
        equivalencelibrary2.add_equivalence(TestGate(*th_2), qc_2)

        QuantumCircuit.tg = tg

        backend = QasmSimulator()
        basis_gates = ['cx', 'u1']
        basis_gates2 = ['cz', 'u1']
        qubits = 2
        q = QuantumRegister(qubits)
        c = ClassicalRegister(qubits)
        register = QuantumCircuit(q, c)

        register.tg(0.5, q[0], q[1])

        circuit = transpile(register,
                backend=backend,
                basis_gates=basis_gates, coupling_map=None, backend_properties=None,
                initial_layout=None, seed_transpiler=None,
                optimization_level=1,
                pass_manager=None, callback=None, output_name=None, equivalence_library=equivalencelibrary)

        circuit2 = transpile(register,
                         backend=backend,
                         basis_gates=basis_gates2, coupling_map=None, backend_properties=None,
                         initial_layout=None, seed_transpiler=None,
                         optimization_level=1,
                         pass_manager=None, callback=None, output_name=None, equivalence_library=equivalencelibrary2)




if __name__ == '__main__':
    unittest.main()

