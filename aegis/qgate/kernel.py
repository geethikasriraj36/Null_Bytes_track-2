
import numpy as np
import pennylane as qml


N_QUBITS = 4
WIRES = list(range(N_QUBITS))

dev = qml.device("default.qubit", wires=N_QUBITS)


def feature_map(x):
    """
    Encode four input features into a four-qubit quantum state.

    Input:
        x: Four real-valued features, each in [0, pi].

    Feature map:
        1. Apply Hadamard gates.
        2. Encode each feature using RZ(x_i).
        3. Apply nearest-neighbor entangling blocks:
           CNOT -> RZ((pi - x_i)*(pi - x_j)) -> CNOT.

    The input is expected to be preprocessed by embed.py.
    """
    x = np.asarray(x, dtype=float)

    if x.shape != (N_QUBITS,):
        raise ValueError("Input must contain exactly four features.")

    if not np.all(np.isfinite(x)):
        raise ValueError("Input features must be finite.")

    if np.any(x < 0) or np.any(x > np.pi):
        raise ValueError("Input features must be in [0, pi].")

    for wire in WIRES:
        qml.Hadamard(wires=wire)

    for wire in WIRES:
        qml.RZ(x[wire], wires=wire)

    for i in range(N_QUBITS - 1):
        j = i + 1
        angle = (np.pi - x[i]) * (np.pi - x[j])

        qml.CNOT(wires=[i, j])
        qml.RZ(angle, wires=j)
        qml.CNOT(wires=[i, j])


@qml.qnode(dev)
def _state_circuit(x):
    """Return the state prepared by the feature map."""
    feature_map(x)
    return qml.state()


def quantum_state(x):
    """Return the four-qubit state vector for input x."""
    return np.asarray(_state_circuit(x), dtype=complex)


def kernel_value(x, y):
    """
    Calculate the fidelity kernel:
        K(x, y) = |<phi(x)|phi(y)>|^2
    """
    state_x = quantum_state(x)
    state_y = quantum_state(y)

    overlap = np.vdot(state_x, state_y)
    value = float(np.abs(overlap) ** 2)

    # Protect against negligible floating-point excursions.
    return float(np.clip(value, 0.0, 1.0))


def gram(X, Y=None):
    """
    Construct a kernel matrix.

    If Y is None, compute the square Gram matrix K(X, X).
    Otherwise, compute the cross-kernel matrix K(X, Y).
    """
    X = np.asarray(X, dtype=float)

    if X.ndim != 2 or X.shape[1] != N_QUBITS:
        raise ValueError("X must have shape (n_samples, 4).")

    if Y is None:
        Y = X
    else:
        Y = np.asarray(Y, dtype=float)

        if Y.ndim != 2 or Y.shape[1] != N_QUBITS:
            raise ValueError("Y must have shape (n_samples, 4).")

    states_X = [quantum_state(row) for row in X]
    states_Y = states_X if Y is X else [quantum_state(row) for row in Y]

    matrix = np.empty((len(X), len(Y)), dtype=float)

    for i, state_x in enumerate(states_X):
        for j, state_y in enumerate(states_Y):
            matrix[i, j] = np.abs(np.vdot(state_x, state_y)) ** 2

    return np.clip(matrix, 0.0, 1.0)


@qml.qnode(dev)
def _overlap(x, y):
    """The circuit real hardware would run: U(x), then U(y)^dagger, then measure.
    P(|0000>) = |<phi(y)|phi(x)>|^2, the same fidelity kernel, without ever reading out a state."""
    feature_map(x)
    qml.adjoint(feature_map)(y)
    return qml.probs(wires=WIRES)


def k_hardware_style(x, y):
    """
    Compute the same kernel the way quantum hardware would: one overlap circuit per pair,
    probability of returning to |0000>. Independent of the state-vector shortcut in gram(),
    so tests can check the two agree. (Exact probabilities here; hardware would estimate them from shots.)
    """
    return float(np.clip(_overlap(np.asarray(x, dtype=float), np.asarray(y, dtype=float))[0], 0.0, 1.0))