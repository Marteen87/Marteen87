from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any


@dataclass
class EvidenceRecord:
    evidence_id: str
    claim: str
    status: str = "VERIFIED"
    source_type: str = "CV"
    source_url: str | None = None
    source_name: str | None = None
    captured_at: str | None = None
    confidence: float = 1.0
    notes: str = ""
    related_claims: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim": self.claim,
            "status": self.status,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "captured_at": self.captured_at,
            "confidence": self.confidence,
            "notes": self.notes,
            "related_claims": self.related_claims,
        }


class EvidenceRegistry:
    def __init__(self, records: list[EvidenceRecord] | None = None):
        self.records = {record.evidence_id: record for record in (records or [])}

    @classmethod
    def from_file(cls, path: str | Path) -> "EvidenceRegistry":
        file_path = Path(path)
        if not file_path.exists():
            return cls()
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        records = [EvidenceRecord(**item) for item in payload.get("records", [])]
        return cls(records=records)

    def add(self, record: EvidenceRecord) -> None:
        self.records[record.evidence_id] = record

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"records": [record.to_dict() for record in self.records.values()]}, ensure_ascii=False, indent=2), encoding="utf-8")

    def supports_claim(self, claim: str) -> list[EvidenceRecord]:
        normalized = self._normalize(claim)
        matches: list[EvidenceRecord] = []
        for record in self.records.values():
            if record.status not in {"VERIFIED", "PARTIAL"}:
                continue
            record_text = self._normalize(record.claim)
            if normalized in record_text or record_text in normalized:
                matches.append(record)
            elif self._token_overlap(record_text, normalized):
                matches.append(record)
        return matches

    def get_by_id(self, evidence_id: str) -> EvidenceRecord | None:
        return self.records.get(evidence_id)

    @staticmethod
    def _normalize(text: str) -> str:
        cleaned = text.lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _token_overlap(left: str, right: str) -> bool:
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return False
        return bool(left_tokens & right_tokens)


DEFAULT_REGISTRY = [
    EvidenceRecord(
        evidence_id="EV-001",
        claim="ventas B2B y gestión de cartera",
        status="VERIFIED",
        source_type="CV",
        source_name="Perfil profesional",
        confidence=0.9,
        notes="Afirmación respaldada por experiencia comercial y gestión de cartera.",
        related_claims=["ventas", "gestión de cartera"],
    ),
    EvidenceRecord(
        evidence_id="EV-002",
        claim="excel y reporting de indicadores",
        status="VERIFIED",
        source_type="CV",
        source_name="Perfil profesional",
        confidence=0.85,
        notes="Reportes e indicadores con Excel/analítica comercial.",
        related_claims=["excel", "kpis"],
    ),
    EvidenceRecord(
        evidence_id="EV-003",
        claim="coordinación operativa y equipos comerciales",
        status="VERIFIED",
        source_type="CV",
        source_name="Perfil profesional",
        confidence=0.88,
        notes="Afirmación respaldada por coordinación y liderazgo operativo.",
        related_claims=["coordinación operativa", "liderazgo"],
    ),
]

