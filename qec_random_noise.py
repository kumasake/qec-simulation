from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error


# =====================================
# エラー率
# =====================================

p = 0.1
shots = 10000


# =====================================
# Xノイズを作る
# =====================================

x_error = pauli_error([
    ('X', p),
    ('I', 1 - p)
])

noise_model = NoiseModel()

noise_model.add_all_qubit_quantum_error(
    x_error,
    ['id']
)


# =====================================
# レジスタ
# =====================================

q = QuantumRegister(5, "q")

syndrome = ClassicalRegister(2, "syn")
output = ClassicalRegister(1, "out")

qc = QuantumCircuit(q, syndrome, output)


# =====================================
# 1. |+>を作る
# =====================================

qc.h(q[0])


# =====================================
# 2. 符号化
# =====================================

qc.cx(q[0], q[1])
qc.cx(q[0], q[2])


# =====================================
# 3. ランダムなXエラー
# =====================================

qc.id(q[0])
qc.id(q[1])
qc.id(q[2])


# =====================================
# 4. シンドローム抽出
# =====================================

# s0 = q0 XOR q1

qc.cx(q[0], q[3])
qc.cx(q[1], q[3])


# s1 = q1 XOR q2

qc.cx(q[1], q[4])
qc.cx(q[2], q[4])


# =====================================
# 5. シンドローム測定
# =====================================

qc.measure(q[3], syndrome[0])
qc.measure(q[4], syndrome[1])


# =====================================
# 6. エラー訂正
# =====================================

# 01 → q0
with qc.if_test((syndrome, 0b01)):
    qc.x(q[0])

# 11 → q1
with qc.if_test((syndrome, 0b11)):
    qc.x(q[1])

# 10 → q2
with qc.if_test((syndrome, 0b10)):
    qc.x(q[2])


# =====================================
# 7. 復号
# =====================================

qc.cx(q[0], q[2])
qc.cx(q[0], q[1])


# =====================================
# 8. |+>に戻ったか確認
# =====================================

qc.h(q[0])

qc.measure(q[0], output[0])


# =====================================
# 9. シミュレーション
# =====================================

simulator = AerSimulator(
    noise_model=noise_model
)

result = simulator.run(
    qc,
    shots=shots
).result()

counts = result.get_counts()

print(counts)


# =====================================
# 10. 論理エラー率を計算
# =====================================

logical_errors = 0

for bitstring, count in counts.items():

    # 複数の古典レジスタがあるので
    # 例: "1 11"
    #
    # 左側がoutput

    output_bit = bitstring.split()[0]

    if output_bit == '1':
        logical_errors += count


logical_error_rate = logical_errors / shots

print()
print("物理エラー率 =", p)
print("論理エラー率 =", logical_error_rate)