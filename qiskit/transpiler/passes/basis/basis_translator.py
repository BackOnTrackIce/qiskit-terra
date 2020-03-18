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

import time
import logging

from heapq import heappush, heappop
from itertools import count as iter_count
from collections import defaultdict

import numpy as np

from qiskit.circuit import Gate, ParameterExpression, ParameterVector, QuantumRegister
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError


logger = logging.getLogger(__name__)

# Names of instructions assumed to supported by any backend.
basic_instrs = ['measure', 'reset', 'barrier', 'snapshot']


class BasisTranslator(TransformationPass):
    """Translates gates to a target basis using a given equivalence library."""

    def __init__(self, equivalence_library, target_basis):
        super().__init__()

        self._equiv_lib = equivalence_library
        self._target_basis = target_basis

    def run(self, dag):
        """Translate an input DAGCircuit to the target basis.

        Args:
            dag (DAGCircuit): input dag

        Raises:
            TranspilerError: if the target basis cannot be reached

        Returns:
            DAGCircuit: output unrolled dag
        """

        target_basis = set(self._target_basis).union(basic_instrs)
        source_basis = set(node.name for node in dag.op_nodes())

        logger.info('Begin BasisTranslator from source basis {} to target '
                    'basis {}.'.format(source_basis, target_basis))

        search_start_time = time.time()
        basis_transforms = _basis_search(self._equiv_lib, source_basis,
                                         target_basis, _basis_heuristic)
        search_end_time = time.time()
        logger.info('Basis translation path search completed in {:.3f}s.'.format(
                search_end_time - search_start_time))

        if basis_transforms is None:
            raise TranspilerError(
                'Unable to map source basis {} to target basis {} '
                'over library {}.'.format(
                    source_basis, target_basis, self._equiv_lib))

        compose_start_time = time.time()
        instr_map = _compose_transforms(basis_transforms, source_basis, dag)

        compose_end_time = time.time()
        logger.info('Basis translation paths composed in {:.3f}s.'.format(
            compose_end_time - compose_start_time))

        for node in dag.op_nodes():
            if node.name in target_basis:
                continue
            elif node.name in instr_map:
                target_params, target_dag = instr_map[node.name]

                if len(node.op.params) != len(target_params):
                    raise RuntimeError(
                        'Translation num_params not equal to op num_params.'
                        'Op: {} {} Translation: {}\n{}'.format(
                            node.op.params, node.op.name,
                            target_params, target))

                # KDK For now, convert target to circ and back to bind parameters.
                # Can add a helper method here with a note that we don't want this on dagcircuit.
                # It's okay here because the circuits are smallish, but its not clear whether the
                # effort of a parameter table on dagcircuit will be worth it.

                from qiskit.converters import dag_to_circuit, circuit_to_dag
                target_circuit = dag_to_circuit(target_dag)

                for target_param, node_param in zip(target_params, node.op.params):
                    if isinstance(node_param, ParameterExpression):
                        target_circuit._substitute_parameters({target_param: node_param})
                    else:
                        target_circuit._bind_parameter(target_param, node_param)

                bound_target_dag = circuit_to_dag(target_circuit)
                if (len(bound_target_dag.op_nodes()) == 1
                        and len(bound_target_dag.op_nodes()[0].qargs) == len(node.qargs)):
                    dag.substitute_node(node, bound_target_dag.op_nodes()[0].op, inplace=True)
                else:
                    dag.substitute_node_with_dag(node, bound_target_dag)
            else:
                raise RuntimeError('BasisTranslator did not map {}.'.format(node.name))

        return dag


def _basis_heuristic(basis, target):
    """Simple metric to gauge distance between two bases."""
    return len(basis ^ target)


def _basis_search(equiv_lib, source_basis, target_basis, heuristic):
    """Search...

    Returns:
       Optional[List[Tuple[]]]: ist of (gate, equiv_params, equiv_circuit) which applied,
    in order will mapp from src to tgt
    None if no path was found.
    """

    source_basis = frozenset(source_basis)
    target_basis = frozenset(target_basis)

    open_set = set()  # Bases found but not yet inspected.
    closed_set = set()  # Bases found and inspected.
    open_heap = []  # Priority queue for inspection order of open_set. Contains
                    # Tuple[priority, count, basis]
    came_from = {}  # Map from bases in closed_set to predecessor with lowest
                    # cost_from_source. Values are
                    # Tuple[prev_basis, gate_name, params, circuit].
    basis_count = iter_count()  # Used break ties in priority.

    open_set.add(source_basis)
    heappush(open_heap, (0, next(basis_count), source_basis))

    # KDK Could drop defaultdict?

    # Map from basis to lowest found cost from source.
    cost_from_source = defaultdict(lambda: np.inf)
    cost_from_source[source_basis] = 0

    # Map from basis to cost_from_source + heuristic.
    est_total_cost = defaultdict(lambda: np.inf)
    est_total_cost[source_basis] = heuristic(source_basis, target_basis)

    logger.debug('Begining basis search from {} to {}.'.format(
        source_basis, target_basis))

    while open_set:
        _, __, current_basis = heappop(open_heap)

        if current_basis in closed_set:
            # When we close a node, we don't remove it from the heap,
            # so skip here.
            continue

        if current_basis.issubset(target_basis):
            # Found target basis. Construct transform path.
            rtn = []
            last_basis = current_basis
            while last_basis != source_basis:
                prev_basis, gate_name, params, equiv = came_from[last_basis]

                rtn.append((gate_name, params, equiv))
                last_basis = prev_basis
            rtn.reverse()

            logger.debug('Transformation path:')
            for gate_name, params, equiv in rtn:
                logger.debug('{} => {}\n{}'.format(gate_name, params, equiv))
            return rtn

        logger.debug('Inspecting basis {}.'.format(current_basis))
        open_set.remove(current_basis)
        closed_set.add(current_basis)

        for gate_name in current_basis:
            equivs = [
                (param, equiv)
                for n in range(20)
                for param, equiv in equiv_lib._get_equivalences((gate_name, n))]

            basis_remain = current_basis - {gate_name}
            neighbors = [
                (frozenset(basis_remain | set(equiv.count_ops())), params, equiv)
                for params, equiv in equivs]

            tentative_cost_from_source = cost_from_source[current_basis] + 1e-3

            for neighbor, params, equiv in neighbors:
                if neighbor in closed_set:
                    continue

                if tentative_cost_from_source >= cost_from_source[neighbor]:
                    continue

                open_set.add(neighbor)
                came_from[neighbor] = (current_basis, gate_name, params, equiv)
                cost_from_source[neighbor] = tentative_cost_from_source
                est_total_cost[neighbor] = tentative_cost_from_source \
                    + heuristic(neighbor, target_basis)
                heappush(open_heap, (est_total_cost[neighbor],
                                     next(basis_count),
                                     neighbor))

    return None


def _compose_transforms(basis_transforms, source_basis, source_dag):
    """Compose a set of basis transforms.

    Args:
        basis_transforms (List[Tuple[gate_name, params, equiv]]): List of transforms to compose.
        source_basis (Set[str]): Names of gates which need to be mapped.

    Returns:
        Dict[gate_name, Tuple(params, dag)]: Mapping between a gate in source_basis and dag to replace it.
            If gate is not included in basis_transforms (because it is in target_basis), it will
            be included as a key to itself. KDK
    """

    example_gates = {node.name: node.op for node in source_dag.op_nodes()}
    mapped_ops = {}

    # KDK Could be dropped and generated only implicitly for source_basis
    for gate_name in source_basis:
        # Need to grab a gate instance to find num_qubits and num_params.
        example_gate = example_gates[gate_name]
        num_params = len(example_gate.params)
        num_qubits = example_gate.num_qubits

        placeholder_params = ParameterVector(gate_name, num_params)
        placeholder_gate = example_gate.copy()#Gate(gate_name, num_qubits, list(placeholder_params))
        placeholder_gate.params = list(placeholder_params)

        dag = DAGCircuit()
        qr = QuantumRegister(num_qubits)
        dag.add_qreg(qr)
        dag.apply_operation_back(placeholder_gate, qr[:], [])
        mapped_ops[gate_name] = placeholder_params, dag

    for gate_name, equiv_params, equiv in basis_transforms:
        logger.debug('Composing transform: {} {} =>\n{}'.format(
            gate_name, equiv_params, equiv))

        for mapped_op_name, (dag_params, dag) in mapped_ops.items():
            doomed_nodes = dag.named_nodes(gate_name)

            if doomed_nodes:
                from qiskit.converters import dag_to_circuit          
                logger.debug('Updating transform {} {} to\n{}'.format(mapped_op_name, dag_params, dag_to_circuit(dag)))

            for node in doomed_nodes:
                from qiskit.converters import circuit_to_dag
                replacement = equiv.copy()

                # KDK Raise if length mismatch
                for equiv_param, node_param in zip(equiv_params, node.op.params):
                    if isinstance(node_param, ParameterExpression):
                        replacement._substitute_parameters({equiv_param: node_param})
                    else:
                        replacement._bind_parameter(equiv_param, node_param)
                replacement_dag = circuit_to_dag(replacement)
                #example_gates.update({node.name: node.op for node in equiv_dag.op_nodes()})
    
                dag.substitute_node_with_dag(node, replacement_dag)

            if doomed_nodes:
                from qiskit.converters import dag_to_circuit
                logger.debug('Updated transform {} {} to\n{}'.format(mapped_op_name, dag_params, dag_to_circuit(dag)))
                
    return mapped_ops
