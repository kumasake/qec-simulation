from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# 量子ビット1個、古典ビット1個
qc = QuantumCircuit(1, 1)

# |0> にHadamardゲートを作用
qc.h(0)

# 量子ビットを測定
qc.measure(0, 0)

# 回路を表示
print(qc)

# シミュレータ
simulator = AerSimulator()

# 1000回実験
result = simulator.run(qc, shots=1000).result()

# 測定結果
counts = result.get_counts(qc)

print(counts)