from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error

import matplotlib.pyplot as plt


# ---------------------------------------
# 実験する物理エラー率
# ---------------------------------------

error_rates = [
    0.001,
    0.005,
    0.01,
    0.02,
    0.05,
    0.10,
    0.15,
    0.20
]

shots = 10000


qec_off_results = []
qec_on_results = []


# =======================================
# エラー率 p を順番に変えて実験
# =======================================

for p in error_rates:

    print("p =", p)

    # -----------------------------------
    # Xエラー
    #
    # p     の確率で X
    # 1 - p の確率で何もしない
    # -----------------------------------

    error = pauli_error([
        ('X', p),
        ('I', 1 - p)
    ])

    noise_model = NoiseModel()

    noise_model.add_all_qubit_quantum_error(
        error,
        ['id']
    )

    simulator = AerSimulator(
        noise_model=noise_model
    )


    # ===================================
    # ① QECなし
    # ===================================

    qc_no_qec = QuantumCircuit(1, 1)

    # |0> に1回ノイズを与える
    qc_no_qec.id(0)

    qc_no_qec.measure(0, 0)

    result = simulator.run(
        qc_no_qec,
        shots=shots
    ).result()

    counts = result.get_counts()

    # |0>を送ったので、1が出たらエラー
    errors = counts.get('1', 0)

    logical_error_rate = errors / shots

    qec_off_results.append(logical_error_rate)


    # ===================================
    # ② 3量子ビットQECあり
    # ===================================

    qc_qec = QuantumCircuit(3, 3)

    # 論理 |0> = |000>
    #
    # 今回は最初から |000> なので
    # 符号化ゲートは特に必要ない

    # 各物理量子ビットにノイズ
    qc_qec.id(0)
    qc_qec.id(1)
    qc_qec.id(2)

    # 測定
    qc_qec.measure([0, 1, 2], [0, 1, 2])

    result = simulator.run(
        qc_qec,
        shots=shots
    ).result()

    counts = result.get_counts()

    logical_errors = 0

    # -----------------------------------
    # 多数決で復号
    # -----------------------------------

    for bitstring, count in counts.items():

        # 例:
        #
        # 000 → 正常
        # 001 → 正常
        # 010 → 正常
        # 100 → 正常
        #
        # 011 → 論理エラー
        # 101 → 論理エラー
        # 110 → 論理エラー
        # 111 → 論理エラー

        number_of_ones = bitstring.count('1')

        if number_of_ones >= 2:
            logical_errors += count


    logical_error_rate = logical_errors / shots

    qec_on_results.append(logical_error_rate)


# =======================================
# 結果表示
# =======================================

print()
print("物理エラー率")
print(error_rates)

print()

print("QECなし")
print(qec_off_results)

print()

print("QECあり")
print(qec_on_results)


# =======================================
# グラフ
# =======================================

plt.plot(
    error_rates,
    qec_off_results,
    marker='o',
    label='Without QEC'
)

plt.plot(
    error_rates,
    qec_on_results,
    marker='o',
    label='3-qubit repetition code'
)

plt.xlabel('Physical error rate p')
plt.ylabel('Logical error rate')
plt.title('Effect of 3-qubit bit-flip code')

plt.legend()
plt.grid()

plt.show()