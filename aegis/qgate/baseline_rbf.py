
from pathlib import Path

import joblib
import numpy as np
from sklearn.svm import SVC


class RBFBaseline:
    """Classical RBF SVM baseline using four-dimensional text features."""

    def __init__(self, C=1.0, gamma="scale"):
        self.model = SVC(
            kernel="rbf",
            C=C,
            gamma=gamma,
            probability=False,
            class_weight="balanced",
            random_state=42,
        )
        self.fitted = False

    @staticmethod
    def _validate_features(X):
        X = np.asarray(X, dtype=float)

        if X.ndim != 2 or X.shape[1] != 4:
            raise ValueError("Features must have shape (n_samples, 4).")

        if not np.all(np.isfinite(X)):
            raise ValueError("Features must contain only finite values.")

        return X

    def fit(self, X, y):
        X = self._validate_features(X)
        y = np.asarray(y)

        if y.ndim != 1 or len(y) != len(X):
            raise ValueError("Labels must be one-dimensional and match X.")

        if len(np.unique(y)) != 2:
            raise ValueError("Training labels must contain exactly two classes.")

        self.model.fit(X, y)
        self.fitted = True
        return self

    def score(self, X):
        """Return raw decision scores, not calibrated probabilities."""
        if not self.fitted:
            raise RuntimeError("Call fit() before score().")

        X = self._validate_features(X)
        return self.model.decision_function(X)

    def predict(self, X):
        if not self.fitted:
            raise RuntimeError("Call fit() before predict().")

        X = self._validate_features(X)
        return self.model.predict(X)

    def save(self, path):
        if not self.fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self, path)

    @classmethod
    def load(cls, path):
        """Load a saved baseline model."""
        instance = joblib.load(path)

        if not isinstance(instance, cls):
            raise TypeError("The saved file is not an RBFBaseline model.")

        return instance