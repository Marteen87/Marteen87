from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ReviewDecision:
    status: str = "PENDING_HUMAN_REVIEW"
    reason: str = "Human approval is required."
    human_review_required: bool = True

class ReviewGate:
    def decide(self, evaluation: dict[str, Any]) -> ReviewDecision:
        # Evaluation can inform a reviewer but cannot approve or submit an application.
        gaps = evaluation.get("critical_gaps", []) or []
        reason = "Evidence gaps require review: " + ", ".join(gaps) if gaps else "Human review is required before any decision."
        return ReviewDecision(reason=reason, human_review_required=True)
