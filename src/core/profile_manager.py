from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

@dataclass
class CandidateProfile:
    candidate_id: str = "candidate-local"
    candidate_name: str = ""
    role_focus: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateProfile":
        allowed = {"candidate_id", "candidate_name", "role_focus", "skills", "experience", "evidence_refs", "unknowns"}
        return cls(**{k: data[k] for k in allowed if k in data})

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "candidate_name": self.candidate_name,
                "role_focus": self.role_focus, "skills": self.skills, "experience": self.experience,
                "evidence_refs": self.evidence_refs, "unknowns": self.unknowns}

class ProfileManager:
    def __init__(self, profile: CandidateProfile | None = None, path: str | Path | None = None):
        self.profile, self.path = profile or CandidateProfile(), Path(path) if path else None

    @classmethod
    def load(cls, path: str | Path) -> "ProfileManager":
        p = Path(path)
        return cls(CandidateProfile.from_dict(json.loads(p.read_text(encoding="utf-8"))), p) if p.exists() else cls(path=p)

    def validate(self) -> dict[str, Any]:
        issues = []
        if not self.profile.candidate_id.strip(): issues.append("candidate_id is required")
        for name in ("role_focus", "skills", "experience", "evidence_refs", "unknowns"):
            if not isinstance(getattr(self.profile, name), list): issues.append(f"{name} must be a list")
        return {"valid": not issues, "issues": issues}

    def save(self) -> None:
        if self.path is None: raise ValueError("A local profile path is required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
