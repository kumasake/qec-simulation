from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


# エラー率
p = 0.1


# ----------------------------
# 1. Xエラーを定義
# ----------------------------

bit_flip_error = pauli_error([
    ('X', p),
    ('I', 1 - p)
])


# ----------------------------
# 2. ノイズモデルを作る
# ----------------------------

noise_model = NoiseModel()

noise_model.add_all_qubit_quantum_error(
    bit_flip_error,
    ['id']
)


# ----------------------------
# 3. 量子回路
# ----------------------------

qc = QuantumCircuit(1, 1)

# 何もしないゲート
qc.id(0)

# 測定
qc.measure(0, 0)


# ----------------------------
# 4. ノイズ付きシミュレータ
# ----------------------------

simulator = AerSimulator(
    noise_model=noise_model
)


# ----------------------------
# 5. 10000回実験
# ----------------------------

result = simulator.run(
    qc,
    shots=10000
).result()

counts = result.get_counts()

print(counts)