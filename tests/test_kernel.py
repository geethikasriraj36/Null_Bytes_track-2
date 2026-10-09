
import numpy as np
import pytest

from aegis.qgate.kernel import gram, kernel_value, quantum_state


def test_state_vector_normalized():
    x = np.array([0.2, 0.7, 1.3, 2.0])
    state = quantum_state(x)

    assert state.shape == (16,)
    assert np.isclose(np.linalg.norm(state), 1.0, atol=1e-9)


def test_kernel_self_similarity_is_one():
    x = np.array([0.2, 0.7, 1.3, 2.0])

    assert np.isclose(kernel_value(x, x), 1.0, atol=1e-9)


def test_kernel_is_symmetric():
    x = np.array([0.2, 0.7, 1.3, 2.0])
    y = np.array([1.0, 0.5, 2.1, 0.9])

    assert np.isclose(kernel_value(x, y), kernel_value(y, x), atol=1e-9)


def test_gram_matrix_diagonal_is_one():
    X = np.array([
        [0.2, 0.7, 1.3, 2.0],
        [1.0, 0.5, 2.1, 0.9],
        [2.0, 1.4, 0.8, 0.3],
    ])

    K = gram(X)

    assert K.shape == (3, 3)
    assert np.allclose(np.diag(K), 1.0, atol=1e-9)


def test_invalid_input_rejected():
    with pytest.raises(ValueError):
        quantum_state([0.1, 0.2, 0.3])

    with pytest.raises(ValueError):
        quantum_state([0.1, 0.2, 0.3, 4.0])


def test_kernel_values_are_bounded():
    x = np.array([0.2, 0.7, 1.3, 2.0])
    y = np.array([1.0, 0.5, 2.1, 0.9])

    value = kernel_value(x, y)

    assert 0.0 <= value <= 1.0