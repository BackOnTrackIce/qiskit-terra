"""Test functionality for the compiler package."""
import random
from pathlib import Path
from typing import Any, Mapping, Iterable, Tuple, TypeVar, List
from unittest import TestCase, mock

import networkx as nx
from qiskit.dagcircuit import DAGCircuit
from qiskit.qasm import Qasm
from qiskit.unroll import Unroller, DAGBackend

import src.mapping.size
import src.permutation.util
import src.mapping.util
from src import mapping as mp, compiler, permutation as pm  # pylint: disable=wrong-import-order
from src.mapping.placement import Placement
from src.permutation import Swap, Permutation
from src.permutation.util import PermutationCircuit, swap_permutation
from src.permutation.general import ApproximateTokenSwapper
from test.test_util import TestUtil  # pylint: disable=wrong-import-order

ArchNode = TypeVar('ArchNode')
_V = TypeVar('_V')
Reg = Tuple[_V, int]
ArchReg = Reg[str]


def _trivial_mapper(dag: DAGCircuit, current_mapping: Mapping) -> Tuple[
    Mapping, PermutationCircuit]:
    """Always returns the trivial (empty) list of swaps."""
    # pylint: disable=unused-argument
    pcircuit = PermutationCircuit(DAGCircuit(), {})
    return current_mapping, pcircuit


class TestCompiler(TestCase):
    """The test cases."""

    def setUp(self) -> None:
        random.seed(0)
        self.circuit: DAGCircuit = TestUtil.basic_dag()
        self.arch_graph = nx.Graph()

    def test_compile_simple(self) -> None:
        """Test if a single CNOT can be compiled on to the architecture 1, 2<->3"""
        self.circuit.add_qreg('q', 3)
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 1)])

        # Only one place to perform the cx
        self.arch_graph.add_edge(2, 3)
        self.arch_graph.add_node(1)

        compiled_circuit, mapping = compiler.compile_to_arch(self.circuit, self.arch_graph,
                                                             _trivial_mapper)
        op_nodes = list(
            filter(lambda n: n[1]["type"] == "op", compiled_circuit.multi_graph.nodes(data=True)))
        self.assertEqual(1, len(op_nodes))
        op_node = op_nodes[0]
        self.assertEqual({2, 3}, {mapping[qarg] for qarg in op_node[1]["qargs"]})

    def test_compile_simple_2(self) -> None:
        """Test whether a Hadamard and CNOT can be compiled to the architecture 1, 2<->3"""
        self.circuit.add_qreg('q', 3)
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 1)])
        self.circuit.apply_operation_back('u2', [('q', 2)], params=['0', 'pi'])  # Hadamard on q[2]

        # Only one place to perform the cx
        self.arch_graph.add_edge(2, 3)
        self.arch_graph.add_node(1)

        compiled_circuit, mapping = compiler.compile_to_arch(self.circuit, self.arch_graph,
                                                             _trivial_mapper)
        node_data = map(lambda n: n[1], compiled_circuit.multi_graph.nodes(data=True))
        op_nodes = list(filter(lambda n: n["type"] == "op", node_data))
        self.assertEqual(2, len(op_nodes))
        arch_nodes = [{mapping[qarg] for qarg in n["qargs"]} for n in op_nodes]

        self.assertCountEqual([{2, 3}, {1}], arch_nodes)

    def test_compile_simple_3(self) -> None:
        """Test whether a sequence of Hadamard and CNOT can be compiled to 0<->1, 2

            A circuit to prepare a Bell state 1/sqrt(2)(|00> + |11>)
        """
        self.circuit.add_qreg('q', 3)
        # Hadamard followed by cx
        self.circuit.apply_operation_back('u2', [('q', 0)], params=['0', 'pi'])  # Hadamard on q[0]
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 1)])

        # Complete graph
        self.arch_graph.add_edge(0, 1)
        self.arch_graph.add_node(2)

        mapper_mock = mock.create_autospec(mp.size.SizeMapper.greedy,
                                           return_value={('q', 0): 0, ('q', 1): 1, ('q', 2): 2})
        with mock.patch('src.mapping.size.SizeMapper.greedy', mapper_mock):
            compiled_circuit, mapping = compiler.compile_to_arch(self.circuit, self.arch_graph,
                                                                 _trivial_mapper)
        op_nodes = list(
            filter(lambda n: n[1]["type"] == "op", compiled_circuit.multi_graph.nodes(data=True)))
        # The mapper may insert a sequence of swaps.
        self.assertEqual(2, len(op_nodes))

        unop_node, binop_node = op_nodes
        self.assertEqual(1, len(unop_node[1]["qargs"]))
        self.assertEqual(2, len(binop_node[1]["qargs"]))
        self.assertEqual({0, 1}, {mapping[qarg] for qarg in binop_node[1]["qargs"]})
        self.assertEqual(0, mapping[unop_node[1]["qargs"][0]])

    def test_compile_too_many_nodes(self) -> None:
        """Test whether the compiler can handle an architecture with too many qubits."""
        self.circuit.add_qreg('q', 3)

        self.arch_graph.add_edge(2, 3)
        self.arch_graph.add_node(1)
        self.arch_graph.add_node(4)

        compiled_circuit, mapping = compiler.compile_to_arch(self.circuit, self.arch_graph,
                                                             _trivial_mapper)
        self.assertEqual(4, len(compiled_circuit.input_map))
        self.assertEqual(4, len(compiled_circuit.output_map))

    def test_compile_cregs(self) -> None:
        """Test the compiler for a circuit with classical registers."""
        self.circuit.add_qreg('q', 2)
        self.circuit.add_creg('c', 2)
        self.circuit.apply_operation_back('u2', [('q', 0)], params=['0', 'pi'])  # Hadamard on q[0]
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 1)])  # Make bell state
        # measure both qubits
        self.circuit.apply_operation_back("measure", [("q", 0)], cargs=[("c", 0)])
        self.circuit.apply_operation_back("measure", [("q", 1)], cargs=[("c", 1)])

        self.arch_graph = nx.complete_graph(2)

        fixed_mapping = {('q', 0): 0, ('q', 1): 1}
        mapper_mock = mock.create_autospec(mp.size.SizeMapper.greedy, return_value=fixed_mapping)
        arch_mapper = mock.MagicMock(return_value=(fixed_mapping,
                                                   PermutationCircuit(DAGCircuit(), {})))

        with mock.patch('src.mapping.size.SizeMapper.greedy', mapper_mock):
            compiled_circuit, mapping = compiler.compile_to_arch(self.circuit,
                                                                 self.arch_graph,
                                                                 arch_mapper)

        node_data = map(lambda n: n[1], compiled_circuit.multi_graph.nodes(data=True))
        op_nodes = list(filter(lambda n: n["type"] == "op", node_data))
        self.assertEqual(4, len(op_nodes))
        [op0, op1, op2, op3] = op_nodes

        self.assertEqual("u2", op0["name"])
        self.assertEqual(0, mapping[op0["qargs"][0]])

        self.assertEqual("cx", op1["name"])
        self.assertEqual({0, 1}, set(mapping[qarg] for qarg in op1["qargs"]))

        self.assertEqual("measure", op2["name"])
        self.assertEqual("measure", op3["name"])
        # The first measurement must be on the control qubit.
        self.assertEqual(mapping[op1["qargs"][0]], mapping[op2["qargs"][0]])
        # The second measurement is on the target qubit.
        self.assertEqual(mapping[op1["qargs"][1]], mapping[op3["qargs"][0]])
        self.assertEqual([("c", 0)], op2["cargs"])
        self.assertEqual([("c", 1)], op3["cargs"])

    def test_compile_swap_needed(self) -> None:
        """Test whether the compiler can perform a circuit that requires a SWAP in the mapping."""
        self.circuit.add_qreg('q', 3)
        self.circuit.add_creg('c', 3)
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 1)])
        self.circuit.apply_operation_back("cx", [("q", 1), ("q", 2)])
        self.circuit.apply_operation_back("cx", [("q", 0), ("q", 2)])
        # Make sure measures come at the end.
        self.circuit.apply_operation_back("barrier", [("q", i) for i in range(3)])
        self.circuit.apply_operation_back("measure", [("q", 0)], [("c", 0)])
        self.circuit.apply_operation_back("measure", [("q", 1)], [("c", 1)])
        self.circuit.apply_operation_back("measure", [("q", 2)], [("c", 2)])
        # Add swaps to the basis so we can select them later.
        self.circuit.add_basis_element("swap", 2)

        # Path graph of 3 nodes.
        self.arch_graph.add_edge(0, 1)
        self.arch_graph.add_edge(1, 2)

        id_mapping = {("q", i): i for i in range(3)}
        mapper_mock = mock.create_autospec(mp.size.SizeMapper.greedy, return_value=id_mapping)

        calls = 0
        swapper = ApproximateTokenSwapper(self.arch_graph.to_undirected())
        def arch_mapper(dag: DAGCircuit, current_mapping: Mapping[Reg[str], int]) \
                -> Tuple[Mapping[Reg[str], int], PermutationCircuit]:
            """The mapper function for a mapping to mapped_to."""
            nonlocal calls
            if calls >= 2:
                mapping = {("q", 0): 1, ("q", 1): 0, ("q", 2): 2}
            else:
                mapping = id_mapping
            calls += 1
            permutation = {i: i for i in self.arch_graph.nodes()}
            Placement(current_mapping, mapping).place(permutation)
            swaps = list(swapper.map(permutation))
            return mapping, pm.util.circuit(([el] for el in swaps), allow_swaps=True)

        with mock.patch('src.mapping.size.SizeMapper.greedy', mapper_mock):
            compiled_circuit, mapping = compiler.compile_to_arch(self.circuit,
                                                                      self.arch_graph,
                                                                      arch_mapper)

        node_data = map(lambda n: n[1], compiled_circuit.multi_graph.nodes(data=True))
        op_nodes = list(filter(lambda n: n["type"] == "op", node_data))
        # Check if the mapping is valid
        for cnot_mapping in (tuple(mapping[qarg] for qarg in n["qargs"])
                             for n in op_nodes if n["name"] == "cx" or n["name"] == "swap"):
            self.assertIn(cnot_mapping, self.arch_graph.edges)
        self.assertEqual(1, len([n for n in op_nodes if n["name"] == "swap"]))

        # Find the mapping
        measure_nodes = dict(
            (n["qargs"][0], n["cargs"][0]) for n in op_nodes if n["name"] == "measure")

        # Check if the cx's are at the right locations
        # We traverse the circuit backwards, keeping the measure_nodes up to date with the swaps.
        arch_nodes = [n for n in op_nodes if n["name"] == "cx" or n["name"] == "swap"]
        expected_cnots = reversed([(0, 1), (1, 2), (0, 2)])
        for arch_node in reversed(arch_nodes):
            if arch_node['name'] == 'swap':
                sw1, sw2 = arch_node["qargs"]
                measure_nodes[sw2], measure_nodes[sw1] = measure_nodes[sw1], measure_nodes[sw2]
            else:
                corrected_qargs = tuple(measure_nodes[qarg][1] for qarg in arch_node["qargs"])
                self.assertEqual(corrected_qargs, next(expected_cnots))

