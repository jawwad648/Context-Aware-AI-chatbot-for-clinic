"""
Lightweight entity extractor (slot filling helpers).
"""
from __future__ import annotations

import re
from datetime import datetime, time
from typing import List, Optional, Tuple

import dateparser


_TIME_RE = re.compile(
    r"\b(?P<h>[01]?\d|2[0-3])(?::(?P<m>[0-5]\d))?\s*(?P<ampm>am|pm)?\b",
    re.IGNORECASE,
)


def extract_datetime(text: str) -> Optional[datetime]:
    if not text:
        return None
    parsed = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    return parsed


def extract_time(text: str) -> Optional[time]:
    m = _TIME_RE.search(text.lower())
    if not m:
        return None
    h = int(m.group("h"))
    mi = int(m.group("m") or 0)
    ampm = m.group("ampm")
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return time(h, mi)
    return None


def extract_doctor(text: str, known_doctors: List[str]) -> Optional[str]:
    low = text.lower()
    for name in known_doctors:
        if name.lower() in low:
            return name
    m = re.search(r"\bdr\.?\s+([a-z][a-z\-']+)", low)
    if m:
        last = m.group(1)
        for name in known_doctors:
            if last in name.lower().split():
                return name
    return None


DEPARTMENTS = [
    "general", "general practice", "gp",
    "dentistry", "dental", "dentist",
    "paediatrics", "pediatrics", "child",
    "cardiology", "heart",
    "dermatology", "skin",
    "ophthalmology", "eye",
    "ent", "ear nose throat",
    "orthopaedics", "orthopedics", "bone",
    "gynaecology", "gynecology", "women",
]


def extract_department(text: str) -> Optional[str]:
    low = text.lower()
    for d in DEPARTMENTS:
        if d in low:
            return d
    return None


_AFFIRM = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "please",
           "go ahead", "confirm", "correct", "that's right", "right"}
_DENY = {"no", "nope", "nah", "cancel", "stop", "don't", "do not", "abort"}


def yes_no(text: str) -> Optional[bool]:
    low = text.strip().lower().rstrip(".!?")
    if low in _AFFIRM:
        return True
    if low in _DENY:
        return False
    for token in _AFFIRM:
        if re.search(rf"\b{re.escape(token)}\b", low):
            return True
    for token in _DENY:
        if re.search(rf"\b{re.escape(token)}\b", low):
            return False
    return None


def extract_name(text: str) -> Optional[Tuple[str, str]]:
    m = re.search(
        r"\b(?:my name is|i am|i'm|this is)\s+([A-Za-z][A-Za-z\-']+)\s+([A-Za-z][A-Za-z\-']+)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).title(), m.group(2).title()
    return None
