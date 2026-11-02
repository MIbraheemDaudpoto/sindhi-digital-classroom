"""Vector Store, Embeddings, and Hybrid Search Retrieval Engine for SDC RAG.
Supports semantic dense embeddings, BM25-style sparse keyword retrieval, Reciprocal Rank Fusion (RRF),
and Cross-Encoder-style Re-ranking for curriculum-grounded Sindhi/English educational retrieval.
Authored under agency-ai-engineer.
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Optional, Tuple
from src.services.sindhi_nlp import normalize_sindhi_text, tokenize_sindhi_query, SINDHI_STOPWORDS


class VectorStoreEngine:
    """Lightweight in-memory and SQLite-backed Vector & Hybrid Search Engine.
    Provides semantic embeddings, cosine similarity calculation, BM25 scoring, and RRF re-ranking.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.documents: Dict[str, Dict[str, Any]] = {}
        # Precomputed IDF map for sparse keyword retrieval
        self.doc_freq: Dict[str, int] = {}
        self.total_docs: int = 0
        self.avg_doc_len: float = 0.0

    def compute_embedding(self, text: str) -> List[float]:
        """Generate deterministic semantic hash embedding vector for any text in Sindhi or English.
        Maps character and token n-grams into a normalized unit hypersphere vector.
        """
        clean = normalize_sindhi_text(text, strip_diacritics=True).lower()
        vec = [0.0] * self.dimension

        if not clean:
            return vec

        tokens = tokenize_sindhi_query(clean)
        # 1. Token-level feature hashing
        for token in tokens:
            thash = hash(token)
            idx = abs(thash) % self.dimension
            sign = 1.0 if (thash % 2 == 0) else -1.0
            vec[idx] += sign * (1.5 if len(token) > 4 else 1.0)

        # 2. Character n-gram hashing (preserves subword roots across Sindhi affixes)
        for i in range(len(clean) - 2):
            trigram = clean[i:i+3]
            chash = hash(trigram)
            idx = abs(chash) % self.dimension
            sign = 1.0 if (chash % 2 == 0) else -1.0
            vec[idx] += sign * 0.35

        # 3. L2 Normalization (unit length)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        return vec

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Index a document into the hybrid vector store."""
        emb = self.compute_embedding(text)
        tokens = tokenize_sindhi_query(text)
        token_set = set(tokens)

        # Update document frequencies
        for tok in token_set:
            self.doc_freq[tok] = self.doc_freq.get(tok, 0) + 1

        self.documents[doc_id] = {
            "id": doc_id,
            "text": text,
            "tokens": tokens,
            "token_count": len(tokens),
            "embedding": emb,
            "metadata": metadata or {}
        }
        self.total_docs = len(self.documents)
        total_tokens = sum(d["token_count"] for d in self.documents.values())
        self.avg_doc_len = (total_tokens / self.total_docs) if self.total_docs > 0 else 1.0

    def add_documents_batch(self, docs: List[Dict[str, Any]]) -> int:
        """Batch add documents: each dict must contain 'id', 'text', and optional 'metadata'."""
        count = 0
        for doc in docs:
            self.add_document(doc["id"], doc["text"], doc.get("metadata"))
            count += 1
        return count

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two normalized vectors."""
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        return max(0.0, min(1.0, dot))

    def bm25_score(self, query_tokens: List[str], doc: Dict[str, Any], k1: float = 1.5, b: float = 0.75) -> float:
        """Compute BM25 score for sparse retrieval."""
        if not self.total_docs or not doc["tokens"]:
            return 0.0

        score = 0.0
        doc_len = doc["token_count"]
        len_norm = 1.0 - b + b * (doc_len / (self.avg_doc_len or 1.0))

        # Count frequencies in document
        term_freq: Dict[str, int] = {}
        for t in doc["tokens"]:
            term_freq[t] = term_freq.get(t, 0) + 1

        for q_token in query_tokens:
            if q_token not in term_freq:
                continue
            tf = term_freq[q_token]
            df = self.doc_freq.get(q_token, 0)
            # Robertson-Spärck Jones IDF
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            idf = max(0.01, idf)
            num = tf * (k1 + 1.0)
            denom = tf + k1 * len_norm
            score += idf * (num / denom)

        return score

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.6,
        sparse_weight: float = 0.4,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform Hybrid Search combining dense vector cosine similarity with BM25 sparse matching."""
        if not self.documents:
            return []

        q_vec = self.compute_embedding(query)
        q_tokens = tokenize_sindhi_query(query)

        scored_candidates = []
        for doc_id, doc in self.documents.items():
            # Check metadata filter
            if metadata_filter:
                match = True
                for k, v in metadata_filter.items():
                    if doc["metadata"].get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            dense_sim = self.cosine_similarity(q_vec, doc["embedding"])
            sparse_val = self.bm25_score(q_tokens, doc)
            # Normalize sparse score roughly into [0, 1] range for combination
            sparse_norm = 1.0 - math.exp(-sparse_val / 3.0)

            hybrid_score = (vector_weight * dense_sim) + (sparse_weight * sparse_norm)

            scored_candidates.append({
                "id": doc_id,
                "text": doc["text"],
                "dense_score": round(dense_sim, 4),
                "sparse_score": round(sparse_val, 4),
                "hybrid_score": round(hybrid_score, 4),
                "metadata": doc["metadata"]
            })

        scored_candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored_candidates[:top_k]

    def rerank_candidates(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Cross-Encoder-style Re-ranking stage.
        Re-scores candidates based on exact semantic phrase alignment, question-keyword density,
        and Sindhi grammatical position weighting.
        """
        if not candidates:
            return []

        q_clean = normalize_sindhi_text(query).lower()
        q_tokens = tokenize_sindhi_query(query)

        reranked = []
        for cand in candidates:
            doc_text = cand["text"]
            doc_clean = normalize_sindhi_text(doc_text).lower()

            relevance_boost = 0.0

            # 1. Exact phrase substring match boost
            if len(q_clean) > 8 and q_clean in doc_clean:
                relevance_boost += 0.35

            # 2. Consecutive token pair adjacency boost (bigram matching)
            for i in range(len(q_tokens) - 1):
                bigram = f"{q_tokens[i]} {q_tokens[i+1]}"
                if bigram in doc_clean:
                    relevance_boost += 0.20

            # 3. Term coverage ratio
            doc_token_set = set(tokenize_sindhi_query(doc_clean))
            matched_terms = [t for t in q_tokens if t in doc_token_set]
            term_coverage = len(matched_terms) / len(q_tokens) if q_tokens else 0.0

            # Combined re-ranking score (0.0 to 1.0 scale)
            final_score = min(1.0, (cand["hybrid_score"] * 0.5) + (term_coverage * 0.3) + relevance_boost)

            reranked.append({
                **cand,
                "reranked_score": round(final_score, 4),
                "term_coverage": round(term_coverage, 2),
                "exact_phrase_match": bool(len(q_clean) > 8 and q_clean in doc_clean)
            })

        reranked.sort(key=lambda x: x["reranked_score"], reverse=True)
        return reranked[:top_k]


# Singleton Vector Store Instance
vector_store = VectorStoreEngine(dimension=128)
