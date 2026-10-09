"""Text -> N_QUBITS numbers in [0, pi]. Same features feed Q-Gate and the RBF baseline (fair comparison)."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import make_pipeline
from aegis.qgate.kernel import N_QUBITS

def make_embedder():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1),
        TruncatedSVD(n_components=N_QUBITS, random_state=0),
        MinMaxScaler(feature_range=(0, np.pi), clip=True),
    )
