
from pathlib import Path

import joblib
import numpy as np
from sklearn.svm import SVC

from aegis.qgate.embed import TextEmbedder
from aegis.qgate.kernel import gram


class QGate:
    """
    Quantum-kernel SVM detector.

    Labels:
        0 = benign
        1 = suspicious / injection

    score() returns a sigmoid-transformed SVM decision margin.
    It is a ranking score, NOT a calibrated probability.
    """

    def __init__(self, C=1.0):
        self.C = C
        self.embedder = TextEmbedder()
        self.model = SVC(
            kernel="precomputed",
            C=C,
            class_weight="balanced",
            probability=False,
            random_state=42,
        )
        self.X_train = None
        self.fitted = False

    @staticmethod
    def _validate_texts(texts):
        if isinstance(texts, str):
            texts = [texts]

        texts = list(texts)

        if not texts:
            raise ValueError("At least one text is required.")

        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError("Texts must be non-empty strings.")

        return texts

    @staticmethod
    def _validate_labels(y, n_samples):
        y = np.asarray(y)

        if y.ndim != 1 or len(y) != n_samples:
            raise ValueError("Labels must match the number of texts.")

        if set(np.unique(y)) != {0, 1}:
            raise ValueError("Labels must contain both classes: 0 and 1.")

        return y.astype(int)

    def fit(self, texts, y):
        """Fit the text embedding pipeline and quantum-kernel SVM."""
        texts = self._validate_texts(texts)
        y = self._validate_labels(y, len(texts))

        features = self.embedder.fit_transform(texts)
        self.X_train = features
        K_train = gram(features)

        self.model.fit(K_train, y)
        self.fitted = True

        return self

    def decision_function(self, texts):
        """Return raw SVM margins for input text."""
        if not self.fitted:
            raise RuntimeError("Call fit() before scoring.")

        texts = self._validate_texts(texts)
        features = self.embedder.transform(texts)

        # Rows represent new texts; columns represent training examples.
        K_test = gram(features, self.X_train)

        return np.asarray(self.model.decision_function(K_test)).reshape(-1)

    def score(self, texts):
        """
        Return a sigmoid-transformed margin in (0, 1).

        This score is not a calibrated attack probability.
        """
        margins = self.decision_function(texts)

        # Numerically stable sigmoid.
        scores = np.empty_like(margins, dtype=float)
        positive = margins >= 0

        scores[positive] = 1.0 / (1.0 + np.exp(-margins[positive]))

        exp_values = np.exp(margins[~positive])
        scores[~positive] = exp_values / (1.0 + exp_values)

        return scores

    def proba(self, texts):
        """Alias for score(); values are not calibrated probabilities."""
        return self.score(texts)

    def predict(self, texts, threshold=0.5):
        """Predict suspicious (1) or benign (0) using the score threshold."""
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be strictly between 0 and 1.")

        return (self.score(texts) >= threshold).astype(int)

    def save(self, path):
        if not self.fitted:
            raise RuntimeError("Cannot save an unfitted QGate.")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path):
        instance = joblib.load(path)

        if not isinstance(instance, cls):
            raise TypeError("The saved file is not a QGate model.")

        return instance