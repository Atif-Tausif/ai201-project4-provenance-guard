"""
Confidence scoring engine.

Combines the two detection signals according to planning.md:

  final_score = (llm_score + stylometric_score) / 2

Thresholds (from planning.md):
  0.00–0.45 → "high_confidence_human"
  0.45–0.70 → "uncertain"
  0.70–1.00 → "high_confidence_ai"

Additional agreement rule (from planning.md):
  "High Confidence AI" is only assigned when BOTH signals independently indicate
  AI-generated writing (both >= 0.5). If they disagree, classification becomes
  "uncertain" regardless of the averaged score.
"""

from dataclasses import dataclass


@dataclass
class ScoringResult:
    llm_score: float
    stylometric_score: float
    confidence: float        # averaged final score
    attribution: str         # "likely_ai" | "likely_human" | "uncertain"
    signals_agree: bool


_THRESHOLD_HUMAN = 0.45
_THRESHOLD_AI    = 0.70


def compute_confidence(llm_score: float, stylometric_score: float) -> ScoringResult:
    """Combine both signals into a final confidence score and attribution label."""
    confidence = round((llm_score + stylometric_score) / 2.0, 4)

    # Both signals must independently agree for a high-confidence AI classification
    signals_agree = (llm_score >= 0.5) == (stylometric_score >= 0.5)

    if confidence < _THRESHOLD_HUMAN:
        attribution = "likely_human"
    elif confidence >= _THRESHOLD_AI and signals_agree and llm_score >= 0.5:
        attribution = "likely_ai"
    else:
        attribution = "uncertain"

    return ScoringResult(
        llm_score=round(llm_score, 4),
        stylometric_score=round(stylometric_score, 4),
        confidence=confidence,
        attribution=attribution,
        signals_agree=signals_agree,
    )
