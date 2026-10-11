"""符号の距離、状態準備、syndrome、測定後の論理状態を検証する。"""

import itertools
import unittest

from qiskit import transpile
from qiskit.quantum_info import StabilizerState
from qiskit_aer import AerSimulator
from qiskit_aer.library import save_expectation_value

from surface_code_d3 import (
    CHECKS, LOGICAL_STATES, LOGICAL_X, LOGICAL_Z, N_DATA,
    build_circuit, data_pauli, expected_syndrome, prepare_logical_state,
    run_verification, verification_cases,
)


def binary_pauli(pauli):
    """位相を無視したPauliの二進表現。積はXORで計算できる。"""
    return tuple(bool(bit) for bit in itertools.chain(pauli.x, pauli.z))


class SurfaceCodeD3Tests(unittest.TestCase):
    def test_code_has_one_logical_qubit_and_distance_three(self):
        generators = [check.pauli for check in CHECKS]
        for left, right in itertools.combinations(generators, 2):
            self.assertTrue(left.commutes(right))
        group = {(False,) * (2 * N_DATA)}
        for generator in generators:
            vector = binary_pauli(generator)
            group |= {tuple(a != b for a, b in zip(item, vector)) for item in group}
        self.assertEqual(len(group), 2**8)  # 独立な8個のcheck: k=9-8=1。
        for logical in (LOGICAL_X, LOGICAL_Z):
            self.assertTrue(all(logical.commutes(check) for check in generators))
            self.assertNotIn(binary_pauli(logical), group)
            self.assertEqual(sum(logical.x | logical.z), 3)
        self.assertTrue(LOGICAL_X.anticommutes(LOGICAL_Z))
        # 重み1、2の全Pauliを調べ、非自明な論理演算がないことを確認。
        for weight in (1, 2):
            for positions in itertools.combinations(range(N_DATA), weight):
                for axes in itertools.product("XYZ", repeat=weight):
                    error = data_pauli("I", ())
                    for axis, position in zip(axes, positions):
                        error = error.compose(data_pauli(axis, (position,)))
                    if all(error.commutes(check) for check in generators):
                        self.assertIn(binary_pauli(error), group)

    def test_preparation_of_both_logical_bases(self):
        for name, (logical, sign) in LOGICAL_STATES.items():
            with self.subTest(state=name):
                state = StabilizerState(prepare_logical_state(name))
                for check in CHECKS:
                    self.assertEqual(state.expectation_value(check.pauli), 1)
                self.assertEqual(state.expectation_value(logical), sign)

    def test_every_single_x_and_z_error_in_all_four_states(self):
        for state in LOGICAL_STATES:
            for report in run_verification(state, shots=4, seed=7):
                with self.subTest(state=state, error=report.case):
                    self.assertTrue(report.passed, report)

    def test_measurement_preserves_data_eigenstate(self):
        # 測定bitだけが正しくても、dataの論理情報を壊す回路は不正。
        simulator = AerSimulator(method="stabilizer")
        circuits, expectations = [], []
        for name, (logical, sign) in LOGICAL_STATES.items():
            for _, error in verification_cases():
                circuit = build_circuit(name, error)
                syndrome = expected_syndrome(error)
                expected = {check.name: 1 - 2 * int(bit) for check, bit in zip(CHECKS, syndrome)}
                for check in CHECKS:
                    save_expectation_value(circuit, check.pauli, list(range(N_DATA)), label=check.name)
                if error is not None and logical.anticommutes(data_pauli(error[0], (error[1],))):
                    logical_sign = -sign
                else:
                    logical_sign = sign
                expected["logical"] = logical_sign
                save_expectation_value(circuit, logical, list(range(N_DATA)), label="logical")
                circuits.append(circuit)
                expectations.append((name, error, expected))
        result = simulator.run(transpile(circuits, simulator, optimization_level=0), shots=1).result()
        self.assertTrue(result.success)
        for index, (name, error, expected) in enumerate(expectations):
            with self.subTest(state=name, error=error):
                for label, sign in expected.items():
                    self.assertAlmostEqual(result.data(index)[label], sign)


if __name__ == "__main__":
    unittest.main()
