from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
from typing import Any

VALID_STATUSES = {"VERIFIED", "PARTIAL", "SELF_REPORTED", "UNKNOWN", "SYNTHETIC"}

@dataclass
class EvidenceRecord:
    evidence_id: str
    claim: str
    status: str
    source: str
    confidence: float
    captured_at: str
    source_url: str = ""
    notes: str = ""
    verified_for: list[str] = field(default_factory=list)
    mapping_reviewed_by: str = ""
    mapping_reviewed_at: str = ""

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid evidence status: {self.status}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.evidence_id or not self.claim or not self.source:
            raise ValueError("evidence_id, claim and source are required")
        if not isinstance(self.verified_for, list) or not all(isinstance(x, str) and x.strip() for x in self.verified_for):
            raise ValueError("verified_for must be a list of non-empty requirement IDs")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class EvidenceRegistry:
    def __init__(self, records: list[EvidenceRecord] | None = None):
        self.records = {r.evidence_id: r for r in (records or [])}

    @classmethod
    def from_file(cls, path: str | Path) -> "EvidenceRegistry":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"records": []}
        return cls([EvidenceRecord(**x) for x in data.get("records", [])])

    def get_by_id(self, evidence_id: str) -> EvidenceRecord | None:
        return self.records.get(evidence_id)

    def supports(self, evidence_ids: list[str], requirement_id: str) -> list[EvidenceRecord]:
        # Authenticity and relevance are separate: a reviewer must explicitly map evidence to a requirement.
        return [
            self.records[x] for x in evidence_ids
            if x in self.records
            and self.records[x].status == "VERIFIED"
            and requirement_id in self.records[x].verified_for
            and bool(self.records[x].mapping_reviewed_by.strip())
            and bool(self.records[x].mapping_reviewed_at.strip())
        ]

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"records": [r.to_dict() for r in self.records.values()]}, ensure_ascii=False, indent=2), encoding="utf-8")
