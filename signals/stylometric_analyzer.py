"""
Signal 2: Stylometric analyzer.

Measures structural/linguistic heuristics and returns a float in [0.0, 1.0]
where 0.0 = very likely human, 1.0 = very likely AI.

Four metrics, each normalized to [0, 1]:

  1. Sentence-length variance (inverted)
     AI text tends to have more uniform sentence lengths.
     Low variance → high AI score.

  2. Type-token ratio (inverted)
     AI text often repeats vocabulary from a narrower set relative to text length.
     Low TTR → high AI score.

  3. Punctuation density (inverted)
     Human writing typically uses more varied punctuation (dashes, ellipses,
     exclamations, questions). AI text skews toward plain periods and commas.
     Low diversity → high AI score.

  4. Transition phrase density
     AI text overuses discourse connectors ("furthermore", "it is important to note",
     "in conclusion", etc.).
     High density → high AI score.

Final score = mean of the four normalized sub-scores.
"""

import math
import re
import string


# Common AI discourse connectors
_TRANSITION_PHRASES = [
    "furthermore", "additionally", "moreover", "it is important to note",
    "it is worth noting", "in conclusion", "to summarize", "in summary",
    "it is essential", "stakeholders", "paradigm", "transformative",
    "it should be noted", "as previously mentioned", "in this context",
    "it is crucial", "equally important", "at the same time",
    "nevertheless", "notwithstanding",
]


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if len(s.split()) >= 2]


def _sentence_length_variance_score(sentences: list[str]) -> float:
    """Low variance → high AI score (returns 0–1)."""
    if len(sentences) < 2:
        return 0.5  # not enough data
    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    # Typical human variance: 20–100; AI: 5–20
    # Map variance to human-likeness, then invert
    normalized_variance = min(variance / 80.0, 1.0)
    return 1.0 - normalized_variance  # high variance = low AI score


def _type_token_ratio_score(tokens: list[str]) -> float:
    """Low TTR → high AI score (returns 0–1)."""
    if len(tokens) < 5:
        return 0.5
    ttr = len(set(tokens)) / len(tokens)
    # TTR naturally shrinks with length; typical range 0.4–0.9
    # Normalize: 0.4 = AI-like, 0.8 = human-like
    normalized = (ttr - 0.4) / 0.4
    normalized = max(0.0, min(1.0, normalized))
    return 1.0 - normalized  # low TTR = high AI score


def _punctuation_diversity_score(text: str) -> float:
    """Low punctuation diversity → high AI score (returns 0–1)."""
    rich_punct = set("!?;:—–…\"'()")
    chars = [c for c in text if c in string.punctuation]
    if not chars:
        return 0.7  # no punctuation is AI-like
    diversity = len(set(chars) & rich_punct) / max(len(rich_punct), 1)
    # diversity 0 = all plain commas/periods → AI; 1 = full variety → human
    return 1.0 - min(diversity / 0.4, 1.0)  # invert


def _transition_density_score(text: str, token_count: int) -> float:
    """High transition phrase density → high AI score (returns 0–1)."""
    lower = text.lower()
    hits = sum(1 for phrase in _TRANSITION_PHRASES if phrase in lower)
    if token_count == 0:
        return 0.0
    density = hits / (token_count / 100.0)  # hits per 100 tokens
    # 0 hits per 100 tokens = human-like, ≥3 = very AI-like
    return min(density / 3.0, 1.0)


def analyze_stylometry(text: str) -> float:
    """Return a stylometric AI likelihood score in [0.0, 1.0]."""
    sentences = _split_sentences(text)
    tokens = re.findall(r"\b\w+\b", text.lower())

    s1 = _sentence_length_variance_score(sentences)
    s2 = _type_token_ratio_score(tokens)
    s3 = _punctuation_diversity_score(text)
    s4 = _transition_density_score(text, len(tokens))

    return round((s1 + s2 + s3 + s4) / 4.0, 4)
