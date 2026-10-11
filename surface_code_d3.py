"""Rotated Surface Code [[9, 1, 3]] の理想的な単一誤り検出モデル。

データの配置:  0 1 2
                3 4 5
                6 7 8
既知の符号状態を準備し、1回のsyndrome抽出を行う。
復号・訂正、確率的ノイズ、fault-tolerantなゲート配置はまだ扱わない。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import Pauli
from qiskit.synthesis import synth_circuit_from_stabilizers
from qiskit_aer import AerSimulator


N_DATA = 9
# 引数なしの実行で使う動作確認用の回数。本実験の統計条件とは別。
DEFAULT_VERIFICATION_SHOTS = 128


@dataclass(frozen=True)
class StabilizerCheck:
    name: str
    axis: str
    qubits: tuple[int, ...]

    @property
    def pauli(self) -> Pauli:
        return data_pauli(self.axis, self.qubits)


def data_pauli(axis: str, qubits: tuple[int, ...]) -> Pauli:
    """QiskitのPauli文字列は、左からq8 ... q0の順。

    人間向けの配置番号とQiskitの文字列順序をここで変換する。
    """
    letters = ["I"] * N_DATA
    for qubit in qubits:
        letters[N_DATA - 1 - qubit] = axis
    return Pauli("".join(letters))


# この順番がsyndromeの表示順・ancillaの割り当て順になる。
CHECKS = (
    StabilizerCheck("X0", "X", (1, 2)),
    StabilizerCheck("X1", "X", (0, 1, 3, 4)),
    StabilizerCheck("X2", "X", (4, 5, 7, 8)),
    StabilizerCheck("X3", "X", (6, 7)),
    StabilizerCheck("Z0", "Z", (0, 3)),
    StabilizerCheck("Z1", "Z", (1, 2, 4, 5)),
    StabilizerCheck("Z2", "Z", (3, 4, 6, 7)),
    StabilizerCheck("Z3", "Z", (5, 8)),
)
LOGICAL_X = data_pauli("X", (0, 3, 6))
LOGICAL_Z = data_pauli("Z", (0, 1, 2))
LOGICAL_STATES = {
    "0": (LOGICAL_Z, 1),
    "1": (LOGICAL_Z, -1),
    "+": (LOGICAL_X, 1),
    "-": (LOGICAL_X, -1),
}
Error = tuple[str, int] | None


def prepare_logical_state(state: str) -> QuantumCircuit:
    """8個の+1 stabilizerと論理X/Zの固有値から既知の状態を準備。

    任意入力のencoderではなく、|0_L>, |1_L>, |+_L>, |-_L>の
    理想的な状態準備。合成回路には非局所ゲートも含まれ得る。
    """
    if state not in LOGICAL_STATES:
        raise ValueError(f"Unknown logical state: {state}")
    logical, sign = LOGICAL_STATES[state]
    generators = [check.pauli.to_label() for check in CHECKS]
    generators.append(("-" if sign == -1 else "") + logical.to_label())
    return synth_circuit_from_stabilizers(generators)


def validate_error(error: Error) -> None:
    if error is not None:
        axis, qubit = error
        if axis not in ("X", "Y", "Z"):
            raise ValueError("Error must be X, Y, or Z.")
        if not isinstance(qubit, int) or not 0 <= qubit < N_DATA:
            raise ValueError("Data qubit index must be an integer from 0 to 8.")


def expected_syndrome(error: Error) -> str:
    """反交換するcheckだけが1になる。表示順はX0..X3, Z0..Z3。

    測定bit 0 = stabilizerの固有値+1、bit 1 = 固有値-1。
    位置が異なっても同じsyndromeになる場合がある（符号の縮退）。
    """
    validate_error(error)
    if error is None:
        return "0" * len(CHECKS)
    axis, qubit = error
    return "".join(
        "1" if qubit in check.qubits and axis != check.axis else "0"
        for check in CHECKS
    )


def build_circuit(state: str = "0", error: Error = None) -> QuantumCircuit:
    validate_error(error)
    data = QuantumRegister(N_DATA, "data")
    ancilla = QuantumRegister(len(CHECKS), "ancilla")
    syndrome = ClassicalRegister(len(CHECKS), "syndrome")
    circuit = QuantumCircuit(data, ancilla, syndrome)
    circuit.compose(prepare_logical_state(state), qubits=list(data), inplace=True)
    circuit.barrier()

    # 符号状態の準備後、測定前に既知の単一Pauli誤りを入れる。
    if error is not None:
        axis, qubit = error
        getattr(circuit, axis.lower())(data[qubit])
    circuit.barrier()

    for index, check in enumerate(CHECKS):
        helper = ancilla[index]
        if check.axis == "X":
            # |+> ancillaをcontrolとするCNOTでXの積を測定する。
            circuit.h(helper)
            for qubit in check.qubits:
                circuit.cx(helper, data[qubit])
            circuit.h(helper)
        else:
            # dataをcontrolとするCNOTでZの積をancillaへ転写する。
            for qubit in check.qubits:
                circuit.cx(data[qubit], helper)
        circuit.measure(helper, syndrome[index])
    return circuit


def verification_cases() -> list[tuple[str, Error]]:
    return [("none", None)] + [
        (f"{axis}@q{qubit}", (axis, qubit))
        for axis in ("X", "Z")
        for qubit in range(N_DATA)
    ]


@dataclass(frozen=True)
class VerificationResult:
    case: str
    expected: str
    counts: dict[str, int]
    shots: int

    @property
    def passed(self) -> bool:
        return self.counts == {self.expected: self.shots}


def run_verification(
    state: str, shots: int, seed: int | None = None
) -> list[VerificationResult]:
    if not isinstance(shots, int) or shots <= 0:
        raise ValueError("shots must be a positive integer.")
    cases = verification_cases()
    circuits = [build_circuit(state, error) for _, error in cases]
    simulator = AerSimulator(method="stabilizer")
    compiled = transpile(circuits, simulator, optimization_level=0)
    simulation = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    if not simulation.success:
        raise RuntimeError(f"Simulation failed: {simulation.status}")
    reports = []
    for index, (name, error) in enumerate(cases):
        # get_counts()はsyndrome[7] ... syndrome[0]。表示用に反転する。
        counts = {bits[::-1]: count for bits, count in simulation.get_counts(index).items()}
        reports.append(VerificationResult(name, expected_syndrome(error), counts, shots))
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shots", type=int, default=DEFAULT_VERIFICATION_SHOTS,
        help="検証用の測定回数（省略時: %(default)s。本実験の設定ではない）",
    )
    parser.add_argument("--state", choices=LOGICAL_STATES, default="0", help="論理状態")
    parser.add_argument("--seed", type=int, help="シミュレータの乱数seed")
    parser.add_argument("--draw", action="store_true", help="誤りなしの回路を表示")
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    if args.draw:
        print(build_circuit(args.state).draw(output="text", fold=120))
    print(f"Rotated Surface Code d=3: 9 data + 8 ancilla, state={args.state}_L")
    print(f"Ideal single-round detection check; shots={args.shots}")
    print("Syndrome order: " + " ".join(check.name for check in CHECKS))
    print("case      expected  observed (count)          result")
    reports = run_verification(args.state, args.shots, args.seed)
    for report in reports:
        observed = ", ".join(f"{bits} ({count})" for bits, count in report.counts.items())
        print(f"{report.case:<9} {report.expected}  {observed:<25} {'PASS' if report.passed else 'FAIL'}")
    passed = sum(report.passed for report in reports)
    print(f"{passed}/{len(reports)} cases passed")
    return 0 if passed == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
