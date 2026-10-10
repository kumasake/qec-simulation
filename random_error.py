import random

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# エラーが発生する確率
p = 0.1


# 3量子ビットを用意
qc = QuantumCircuit(3, 3)


# ---------------------------
# 符号化
# |1> → |111>
# ---------------------------

qc.x(0)

qc.cx(0, 1)
qc.cx(0, 2)


# ---------------------------
# ランダムなXエラー
# ---------------------------

if random.random() < p:
    qc.x(1)
    print("q1にXエラーが発生しました")
else:
    print("エラーは発生しませんでした")


# ---------------------------
# 測定
# ---------------------------

qc.measure([0, 1, 2], [0, 1, 2])


# ---------------------------
# シミュレーション
# ---------------------------

simulator = AerSimulator()

result = simulator.run(
    qc,
    shots=1
).result()

print(result.get_counts())