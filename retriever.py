"""
Semantic FAQ retriever (minimal RAG).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class FaqMatch:
    question: str
    answer: str
    score: float


class FaqRetriever:
    MIN_SCORE = 0.40

    def __init__(self, model: SentenceTransformer, faq_path: str) -> None:
        self.model = model
        self.faq_path = faq_path
        self._questions: List[str] = []
        self._answers: List[str] = []
        self._embeddings: Optional[np.ndarray] = None
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.faq_path):
            raise FileNotFoundError(self.faq_path)
        with open(self.faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            self._questions.append(entry["question"])
            self._answers.append(entry["answer"])
        self._embeddings = self.model.encode(
            self._questions,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    def search(self, query: str, k: int = 1) -> List[FaqMatch]:
        if not self._questions:
            return []
        q_emb = self.model.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        sims = self._embeddings @ q_emb
        idx = np.argsort(-sims)[:k]
        return [
            FaqMatch(
                question=self._questions[i],
                answer=self._answers[i],
                score=float(sims[i]),
            )
            for i in idx
        ]

    def best(self, query: str) -> Optional[FaqMatch]:
        hits = self.search(query, k=1)
        if not hits:
            return None
        return hits[0] if hits[0].score >= self.MIN_SCORE else None
