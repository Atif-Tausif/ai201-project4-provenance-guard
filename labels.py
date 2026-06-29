"""
Transparency label generator.

Maps (attribution, confidence) to the three label variants defined in planning.md.
Returns a dict with the display title and the explanatory message shown to users.
"""

from dataclasses import dataclass


@dataclass
class TransparencyLabel:
    title: str
    message: str
    attribution: str   # "likely_ai" | "likely_human" | "uncertain"


_LABELS = {
    "likely_ai": TransparencyLabel(
        title="Likely AI-Generated",
        message=(
            "Our analysis indicates with high confidence that this content was generated "
            "using AI. This decision is based on multiple independent detection methods."
        ),
        attribution="likely_ai",
    ),
    "likely_human": TransparencyLabel(
        title="Likely Human-Written",
        message=(
            "Our analysis indicates with high confidence that this content was written "
            "by a human. This decision is based on multiple independent detection methods."
        ),
        attribution="likely_human",
    ),
    "uncertain": TransparencyLabel(
        title="Uncertain",
        message=(
            "Our analysis found mixed or inconclusive evidence. The system cannot "
            "confidently determine whether this content was AI-generated or human-written."
        ),
        attribution="uncertain",
    ),
}


def generate_label(attribution: str) -> TransparencyLabel:
    """Return the transparency label for a given attribution string."""
    if attribution not in _LABELS:
        raise ValueError(f"Unknown attribution value: {attribution!r}")
    return _LABELS[attribution]
