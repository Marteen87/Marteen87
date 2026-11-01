from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class CandidateProfile:
    candidate_name: str = "Candidato"
    role_focus: list[str] = field(default_factory=list)
    verified_skills: list[str] = field(default_factory=list)
    verified_experience: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "role_focus": self.role_focus,
            "verified_skills": self.verified_skills,
            "verified_experience": self.verified_experience,
            "unknowns": self.unknowns,
            "constraints": self.constraints,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CandidateProfile":
        return cls(
            candidate_name=str(payload.get("candidate_name", "Candidato")),
            role_focus=list(payload.get("role_focus", []) or []),
            verified_skills=list(payload.get("verified_skills", []) or []),
            verified_experience=list(payload.get("verified_experience", []) or []),
            unknowns=list(payload.get("unknowns", []) or []),
            constraints=list(payload.get("constraints", []) or []),
            evidence_refs=list(payload.get("evidence_refs", []) or []),
        )


class ProfileManager:
    def __init__(self, path: str | Path | None = None, profile: CandidateProfile | None = None):
        self.path = Path(path) if path is not None else None
        self.profile = profile or CandidateProfile()

    @classmethod
    def load(cls, path: str | Path) -> "ProfileManager":
        file_path = Path(path)
        payload = json.loads(file_path.read_text(encoding="utf-8")) if file_path.exists() else {}
        return cls(path=file_path, profile=CandidateProfile.from_dict(payload))

    def save(self) -> None:
        if self.path is None:
            raise ValueError("ProfileManager.path is required before saving.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def validate(self) -> dict[str, Any]:
        issues: list[str] = []
        if not self.profile.candidate_name.strip():
            issues.append("candidate_name is required")
        if not isinstance(self.profile.verified_skills, list):
            issues.append("verified_skills must be a list")
        if not isinstance(self.profile.verified_experience, list):
            issues.append("verified_experience must be a list")
        return {
            "valid": not issues,
            "issues": issues,
            "profile": self.profile.to_dict(),
        }

    def add_skill(self, skill: str) -> None:
        if skill and skill not in self.profile.verified_skills:
            self.profile.verified_skills.append(skill)

    def add_evidence_ref(self, evidence_ref: str) -> None:
        if evidence_ref and evidence_ref not in self.profile.evidence_refs:
            self.profile.evidence_refs.append(evidence_ref)


DEFAULT_PROFILE = CandidateProfile(
    candidate_name="Candidato",
    role_focus=["AI Operations", "Commercial Operations", "Automation"],
    verified_skills=[
        "ventas",
        "negociación",
        "gestión de cartera",
        "excel",
        "automatización",
        "coordinación operativa",
    ],
    verified_experience=[
        "ventas B2B",
        "gestión de cartera",
        "coordinación operativa",
    ],
    unknowns=["inglés certificado", "automatización en producción"],
    constraints=["no inventar experiencia no documentada", "mantener evidencia verificable"],
    evidence_refs=[],
).to_dict()

