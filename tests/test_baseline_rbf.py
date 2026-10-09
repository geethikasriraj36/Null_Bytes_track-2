
import numpy as np
import pytest

from aegis.qgate.baseline_rbf import RBFBaseline


X = np.array([
    [0.1, 0.2, 0.3, 0.4],
    [0.2, 0.3, 0.4, 0.5],
    [0.3, 0.2, 0.1, 0.4],
    [0.4, 0.5, 0.6, 0.7],
    [2.5, 2.4, 2.3, 2.2],
    [2.4, 2.3, 2.2, 2.1],
    [2.3, 2.5, 2.4, 2.2],
    [2.2, 2.1, 2.5, 2.4],
])

Y = np.array([0, 0, 0, 0, 1, 1, 1, 1])


def test_fit_and_score():
    model = RBFBaseline().fit(X, Y)

    scores = model.score(X)
    predictions = model.predict(X)

    assert scores.shape == (len(X),)
    assert predictions.shape == Y.shape
    assert np.all(np.isfinite(scores))


def test_model_save_and_load(tmp_path):
    model = RBFBaseline().fit(X, Y)
    path = tmp_path / "baseline.joblib"

    model.save(path)
    loaded = RBFBaseline.load(path)

    assert np.allclose(model.score(X), loaded.score(X))
    assert np.array_equal(model.predict(X), loaded.predict(X))


def test_unfitted_model_rejected():
    model = RBFBaseline()

    with pytest.raises(RuntimeError):
        model.score(X)


def test_invalid_feature_shape_rejected():
    model = RBFBaseline()

    with pytest.raises(ValueError):
        model.fit(np.zeros((8, 3)), Y)