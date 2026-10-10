from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# 3量子ビット、3古典ビット
qc = QuantumCircuit(3, 3)

# -------------------------
# 1. 初期状態 |000>
# -------------------------

# -------------------------
# 2. 符号化
# |0> → |000>
# -------------------------
qc.cx(0, 1)
qc.cx(0, 2)

# -------------------------
# 3. エラーを意図的に発生
# 量子ビット1を反転
# -------------------------
qc.x(1)

# -------------------------
# 4. 測定T
# -------------------------
qc.measure([0, 1, 2], [0, 1, 2])

print(qc)

simulator = AerSimulator()

result = simulator.run(
    qc,
    shots=1000
).result()

counts = result.get_counts()

print(counts)                                                                                                                   