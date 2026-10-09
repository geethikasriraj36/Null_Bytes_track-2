"""Quantum feature map + fidelity kernel (PennyLane simulator).

Each text becomes N_QUBITS numbers in [0, pi]. Each number rotates one qubit (Hadamard + RZ).
CNOT-RZ-CNOT blocks entangle neighbouring qubits so the kernel also sees PAIRS of features.

Kernel value k(a, b) = |<phi(a)|phi(b)>|^2  (fidelity: 1 = same state, 0 = orthogonal).

Two ways to compute it, same numbers:
  * overlap circuit  : run phi(a) then phi(b)^dagger, measure P(all zeros). This is how real
                       quantum hardware would do it. Needs one circuit per PAIR -> n^2 circuits.
  * statevector trick: on a simulator, get the state of phi(x) once per sample and take dot
                       products. n circuits instead of n^2. Used by default for speed.
"""
import numpy as np
import pennylane as qml

N_QUBITS = 4
dev = qml.device("default.qubit", wires=N_QUBITS)

def feature_map(x):
    for i in range(N_QUBITS):
        qml.Hadamard(wires=i)
        qml.RZ(x[i], wires=i)
    for i in range(N_QUBITS - 1):
        qml.CNOT(wires=[i, i + 1])
        qml.RZ((np.pi - x[i]) * (np.pi - x[i + 1]), wires=i + 1)
        qml.CNOT(wires=[i, i + 1])

@qml.qnode(dev)
def _state(x):
    feature_map(x)
    return qml.state()

@qml.qnode(dev)
def _overlap(x1, x2):
    feature_map(x1)
    qml.adjoint(feature_map)(x2)
    return qml.probs(wires=range(N_QUBITS))

def k_hardware_style(x1, x2) -> float:
    """The overlap-circuit version. Use it on a slide / to prove the trick gives the same value."""
    return float(_overlap(x1, x2)[0])

def states(X) -> np.ndarray:
    return np.array([_state(x) for x in X])

def gram(A, B=None) -> np.ndarray:
    """Kernel matrix |<phi(a)|phi(b)>|^2 for all pairs. B=None means A vs A (training)."""
    SA = states(A)
    SB = SA if B is None else states(B)
    return np.abs(SA.conj() @ SB.T) ** 2
