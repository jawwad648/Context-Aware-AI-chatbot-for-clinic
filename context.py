"""
Conversation context / dialogue state manager.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, Optional


MAX_HISTORY = 12


@dataclass
class Turn:
    role: str
    text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationState:
    session_id: str
    history: Deque[Turn] = field(default_factory=lambda: deque(maxlen=MAX_HISTORY))
    flow: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    last_intent: Optional[str] = None
    last_confidence: float = 0.0

    def add_user(self, text: str) -> None:
        self.history.append(Turn("user", text))

    def add_bot(self, text: str) -> None:
        self.history.append(Turn("bot", text))

    def reset_flow(self) -> None:
        self.flow = None
        self.slots = {}

    def recent_user_text(self, n: int = 3) -> str:
        buf = [t.text for t in self.history if t.role == "user"][-n:]
        return " ".join(buf)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "flow": self.flow,
            "slots": self.slots,
            "turns": len(self.history),
        }


class ContextStore:
    def __init__(self) -> None:
        self._store: Dict[str, ConversationState] = {}

    def get(self, session_id: str) -> ConversationState:
        if session_id not in self._store:
            self._store[session_id] = ConversationState(session_id=session_id)
        return self._store[session_id]

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def all_sessions(self) -> Dict[str, ConversationState]:
        return dict(self._store)
