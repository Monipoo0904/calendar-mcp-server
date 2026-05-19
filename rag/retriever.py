"""rag/retriever.py
Pure-Python TF-IDF retriever — no external vector DB or embeddings required.

Used by main.py to power knowledge base search (RAG layer).
For production: replace retrieve_chunks() with a pgvector / Pinecone /
Weaviate call that uses real dense embeddings.

Pipeline:
  query text
    → tokenize()
    → compute_tf()  +  build_idf(corpus)
    → tfidf_vector()
    → cosine_sim() vs every document vector
    → top-k ranked results
"""

import math
import re
from typing import Dict, List

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, return word tokens."""
    return _TOKEN_RE.findall(text.lower())


def compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Term frequency: count / total tokens."""
    if not tokens:
        return {}
    freq: Dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    n = len(tokens)
    return {t: c / n for t, c in freq.items()}


def build_idf(corpus: List[List[str]]) -> Dict[str, float]:
    """Inverse document frequency over a tokenised corpus.

    Uses add-one (Laplace) smoothing so unseen terms get a non-zero weight.
    """
    n = len(corpus)
    df: Dict[str, int] = {}
    for doc_tokens in corpus:
        for term in set(doc_tokens):
            df[term] = df.get(term, 0) + 1
    return {
        term: math.log((n + 1) / (count + 1)) + 1
        for term, count in df.items()
    }


def tfidf_vector(
    tf: Dict[str, float], idf: Dict[str, float]
) -> Dict[str, float]:
    """Multiply TF × IDF for each term."""
    return {term: tf_val * idf.get(term, 1.0) for term, tf_val in tf.items()}


def cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def retrieve_chunks(
    query: str, docs: List[Dict], top_k: int = 3
) -> List[Dict]:
    """Return the top_k most relevant docs for *query* using TF-IDF cosine similarity.

    Each doc dict must have a 'content' key.
    An optional 'title' key is concatenated into the scoring text.

    Returns an empty list when docs is empty or no doc has a positive score.
    """
    if not docs:
        return []

    corpus = [
        tokenize((d.get("title", "") + " " + d.get("content", "")).strip())
        for d in docs
    ]
    idf = build_idf(corpus)

    q_tokens = tokenize(query)
    q_vec = tfidf_vector(compute_tf(q_tokens), idf)

    scored: List[tuple] = []
    for i, doc in enumerate(docs):
        doc_vec = tfidf_vector(compute_tf(corpus[i]), idf)
        score = cosine_sim(q_vec, doc_vec)
        scored.append((score, doc))

    scored.sort(key=lambda x: -x[0])
    return [doc for score, doc in scored[:top_k] if score > 0]
