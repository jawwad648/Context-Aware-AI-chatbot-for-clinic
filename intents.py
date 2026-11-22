"""
Semantic intent classifier using a pretrained sentence-transformer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


INTENT_EXAMPLES: Dict[str, List[str]] = {
    "greeting": [
        "hello", "hi there", "hey", "good morning", "good afternoon",
        "hi, are you there?", "hello chatbot",
    ],
    "goodbye": [
        "bye", "goodbye", "thanks, bye", "see you", "that's all thanks",
        "ok, thank you, goodbye",
    ],
    "thanks": [
        "thanks", "thank you", "appreciate it", "thanks a lot", "ta",
    ],
    "book_appointment": [
        "I want to book an appointment",
        "can I schedule a visit with a doctor",
        "I need to see a doctor",
        "book me in with Dr Smith",
        "I'd like to make an appointment for tomorrow",
        "schedule a consultation please",
        "can I get an appointment this week",
    ],
    "cancel_appointment": [
        "cancel my appointment",
        "I can't make my appointment",
        "please cancel my booking for Monday",
        "I want to cancel my visit",
    ],
    "reschedule_appointment": [
        "reschedule my appointment",
        "can we move my appointment to Friday",
        "change my appointment time",
        "I need to shift my booking",
    ],
    "check_appointment": [
        "when is my next appointment",
        "do I have an appointment",
        "what time is my visit",
        "check my booking",
    ],
    "lab_results": [
        "can I get my lab results",
        "I want to see my blood test results",
        "are my test results ready",
        "show me my pathology report",
        "what were my lab findings",
    ],
    "clinic_info": [
        "what are your opening hours",
        "where is the clinic",
        "do you take insurance",
        "how much is a consultation",
        "which doctors do you have",
        "what services do you offer",
        "is there parking",
    ],
    "symptom_query": [
        "I have a headache what should I do",
        "my throat hurts",
        "I've been feeling dizzy",
        "I have a fever",
        "my stomach is upset",
    ],
    "human_handoff": [
        "I want to speak to a human",
        "connect me to the receptionist",
        "can I talk to a real person",
        "transfer me to staff",
    ],
}


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    nearest_example: str


class IntentClassifier:
    MIN_CONFIDENCE = 0.45

    def __init__(self, model: SentenceTransformer) -> None:
        self.model = model
        self._labels: List[str] = []
        self._examples: List[str] = []
        for intent, examples in INTENT_EXAMPLES.items():
            for ex in examples:
                self._labels.append(intent)
                self._examples.append(ex)
        self._embeddings = self.model.encode(
            self._examples,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    def predict(self, message: str) -> IntentPrediction:
        q = self.model.encode(
            [message], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        sims = self._embeddings @ q
        best = int(np.argmax(sims))
        return IntentPrediction(
            intent=self._labels[best],
            confidence=float(sims[best]),
            nearest_example=self._examples[best],
        )

    def topk(self, message: str, k: int = 3) -> List[Tuple[str, float]]:
        q = self.model.encode(
            [message], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        sims = self._embeddings @ q
        idx = np.argsort(-sims)[:k]
        return [(self._labels[i], float(sims[i])) for i in idx]
