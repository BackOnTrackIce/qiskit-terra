# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Standard gates."""

from .barrier import Barrier
from .h import HGate, CHGate
from .i import IGate
from .ms import MSGate
from .r import RGate
from .rx import RXGate, CRXGate
from .rxx import RXXGate
from .ry import RYGate, CRYGate
from .ryy import RYYGate
from .rz import RZGate, CRZGate
from .rzz import RZZGate
from .rzx import RZXGate
from .s import SGate, SdgGate
from .swap import SwapGate, CSwapGate
from .iswap import iSwapGate
from .dcx import DCXGate
from .t import TGate, TdgGate
from .u1 import U1Gate, CU1Gate, MCU1Gate
from .u2 import U2Gate
from .u3 import U3Gate, CU3Gate
from .x import (
    XGate, CXGate, CCXGate, RCCXGate, C3XGate, RC3XGate, C4XGate,
    MCXGate, MCXGrayCode, MCXRecursive, MCXVChain
)
from .y import YGate, CYGate
from .z import ZGate, CZGate

# to be converted to gates
from .boolean_logical_gates import logical_or, logical_and
from .multi_control_rotation_gates import mcrx, mcry, mcrz

# deprecated gates, to be removed
from .i import IdGate
from .x import ToffoliGate
from .swap import FredkinGate
from .x import CnotGate
from .y import CyGate
from .z import CzGate
from .u1 import Cu1Gate
from .u3 import Cu3Gate
from .rx import CrxGate
from .ry import CryGate
from .rz import CrzGate


from math import pi
from collections import defaultdict, namedtuple
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.circuit import ParameterVector as _pv, QuantumCircuit as _qc, QuantumRegister as _qr

def returnStandardRules():
    Entry = namedtuple('Entry', ['search_base',
                                 'equivs'])

    StandardRules = defaultdict(lambda: Entry(True, []))

    reg = _qr(3, 'q')
    circ = _qc(reg)
    circ.h(0)
    circ.cx(1, 2)
    circ.tdg(2)
    circ.cx(0, 2)
    circ.t(2)
    circ.cx(1, 2)
    circ.tdg(2)
    circ.cx(0, 2)
    circ.t(1)
    circ.t(2)
    circ.h(2)
    circ.cx(0, 1)
    circ.t(0)
    circ.tdg(1)
    circ.cx(0, 1)
    gate = ToffoliGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(3, 'q')
    circ = _qc(reg)
    circ.cx(2, 1)
    circ.ccx(0, 1, 2)
    circ.cx(2, 1)
    gate = FredkinGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    circ.sdg(1)
    circ.cx(0, 1)
    circ.s(1)
    gate = CyGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    circ.h(1)
    circ.cx(0, 1)
    circ.h(1)
    gate = CzGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    circ.cx(0, 1)
    circ.cx(1, 0)
    circ.cx(0, 1)
    gate = SwapGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u2(0, pi, 0)
    gate = HGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u1(pi / 2, 0)
    gate = SGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u1(- pi / 2, 0)
    gate = SdgGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u1(pi / 4, 0)
    gate = TGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u1(- pi / 4, 0)
    gate = TdgGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.u3(0, 0, p[0], 0)
    gate = U1Gate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 2)
    circ.u3(pi / 2, p[0], p[1], 0)
    gate = U2Gate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u3(pi, 0, pi, 0)
    gate = XGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    circ.u3(pi, pi/2, pi/2, 0)
    gate = YGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 2)
    circ.u3(p[0], p[1] - pi / 2, -p[1] + pi / 2, 0)
    gate = RGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.r(p[0], 0, 0)
    gate = RXGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.r(p[0], pi/2, 0)
    gate = RYGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.u1(p[0], 0)
    gate = RZGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.u1(p[0] / 2, 0)
    circ.cx(0, 1)
    circ.u1(-p[0] / 2, 1),
    circ.cx(0, 1)
    circ.u1(p[0] / 2, 1)
    gate = Cu1Gate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    circ.s(1)
    circ.h(1)
    circ.t(1)
    circ.cx(0, 1)
    circ.tdg(1)
    circ.h(1)
    circ.sdg(1)
    gate = CHGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.u1(p[0] / 2, 1)
    circ.cx(0, 1)
    circ.u1(-p[0] / 2, 1)
    circ.cx(0, 1)
    gate = CrzGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    p = _pv('th', 3)
    circ.u1((p[2] + p[1]) / 2, 0)
    circ.u1((p[2] - p[1]) / 2, 1)
    circ.cx(0, 1)
    circ.u3(-p[0] / 2, 0, -(p[1] + p[2]) / 2, 1)
    circ.cx(0, 1)
    circ.u3(p[0] / 2, p[1], 0, 1)
    gate = Cu3Gate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.u3(pi / 2, p[0], 0, 0)
    circ.h(1)
    circ.cx(0, 1)
    circ.u1(-p[0], 1),
    circ.cx(0, 1)
    circ.h(1)
    circ.u2(-pi, pi - p[0], 0)
    gate = RXXGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    p = _pv('th', 1)
    circ.cx(0, 1)
    circ.u1(p[0], 1)
    circ.cx(0, 1)
    gate = RZZGate(*p)
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))


    for n_qubits in range(2, 13):
        reg = _qr(n_qubits, 'q')
        circ = _qc(reg)
        th = _pv('th', 1)  # since we're inspecting param name, could re-use already
        gate = MSGate(n_qubits, *th)
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                circ.u3(pi / 2, p[0], 0, i)
                circ.h(j)
                circ.cx(i, j)
                circ.u1(-p[0], j),
                circ.cx(i, j)
                circ.h(j)
                circ.u2(-pi, pi - p[0], i)

        StandardRules[(gate.name, gate.num_qubits)].equivs.append(
            (gate.params.copy(), circ.copy()))

    reg = _qr(2, 'q')
    circ = _qc(reg)
    circ.h(1)
    circ.cz(0, 1)
    circ.h(1)
    gate = CnotGate()
    StandardRules[(gate.name, gate.num_qubits)].equivs.append(
        (gate.params.copy(), circ.copy()))


    reg = _qr(1, 'q')
    circ = _qc(reg)
    p = _pv('th', 3)
    circ.rz(p[0], 0)
    circ.rx(pi / 2, 0)
    circ.rz(p[1] + pi, 0)
    circ.rx(pi / 2, 0)
    circ.rz(p[2] + pi, 0)
    StandardRules[(U3Gate(*p).name, U3Gate(*p).num_qubits)].equivs.append(
        (U3Gate(*p).params.copy(), circ.copy()))

    return StandardRules


SessionEquivalenceLibrary.initialize_base(returnStandardRules())