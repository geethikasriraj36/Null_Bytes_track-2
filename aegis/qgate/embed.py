
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler


N_FEATURES = 4


class TextEmbedder:
    """Convert text into four numerical features in [0, pi]."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 5),
            min_df=1,
            dtype=np.float64,
        )
        self.svd = None
        self.scaler = MinMaxScaler(feature_range=(0.0, np.pi))
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

    def fit(self, texts):
        """Learn the vectorizer, SVD and scaling parameters from training text."""
        texts = self._validate_texts(texts)

        if len(texts) < 5:
            raise ValueError("Provide at least five training texts.")

        tfidf = self.vectorizer.fit_transform(texts)

        max_components = min(
            N_FEATURES,
            tfidf.shape[0] - 1,
            tfidf.shape[1] - 1,
        )

        if max_components < N_FEATURES:
            raise ValueError(
                "Not enough samples or distinct character n-grams "
                "to fit four SVD components."
            )

        self.svd = TruncatedSVD(
            n_components=N_FEATURES,
            random_state=42,
        )

        reduced = self.svd.fit_transform(tfidf)
        self.scaler.fit(reduced)
        self.fitted = True

        return self

    def transform(self, texts):
        """Transform text using parameters learned during fit."""
        if not self.fitted:
            raise RuntimeError("Call fit() before transform().")

        texts = self._validate_texts(texts)
        tfidf = self.vectorizer.transform(texts)
        reduced = self.svd.transform(tfidf)
        features = self.scaler.transform(reduced)

        return np.clip(features, 0.0, np.pi)

    def fit_transform(self, texts):
        """Fit the embedder and return transformed training features."""
        return self.fit(texts).transform(texts)