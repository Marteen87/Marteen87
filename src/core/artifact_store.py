from __future__ import annotations

import re
from typing import Any

from src.core.evidence_registry import EvidenceRegistry


def _normalize_requirement(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_requirements(vacancy: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for field_name in ("requirements", "description", "title"):
        raw = vacancy.get(field_name, "")
        if raw:
            split_parts = re.split(r"[;\n]+|\s*\.\s*", str(raw))
            parts.extend(part.strip() for part in split_parts if part.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for item in parts:
        normalized = _normalize_requirement(item)
        if normalized and normalized not in seen:
            deduped.append(item)
            seen.add(normalized)
    return deduped


def evaluate_vacancy(vacancy: dict[str, Any], profile: dict[str, Any], evidence_registry: EvidenceRegistry) -> dict[str, Any]:
    requirements = _extract_requirements(vacancy)
    if not requirements:
        return {
            "overall_score": 0,
            "mandatory_requirements_met": 0,
            "mandatory_requirements_total": 0,
            "evidence_coverage": 0,
            "critical_gaps": ["No se pudieron extraer requisitos verificables de la vacante."],
            "verified_strengths": [],
            "unknowns": ["requisitos no informados"],
            "recommendation": "DO_NOT_APPLY",
            "explanation": "La vacante no aporta requisitos suficientes para evaluarla con trazabilidad.",
        }

    social_knowledge = set((profile.get("verified_skills") or []) + (profile.get("verified_experience") or []))
    verified_strengths: list[str] = []
    critical_gaps: list[str] = []
    matched_count = 0

    for requirement in requirements:
        requirement_norm = _normalize_requirement(requirement)
        support = next(
            (record for record in evidence_registry.supports_claim(requirement) if record.claim.lower() in str(requirement).lower() or requirement_norm in _normalize_requirement(record.claim)),
            None,
        )
        if support is not None:
            verified_strengths.append(requirement)
            matched_count += 1
        elif any(
            _normalize_requirement(skill) in requirement_norm or requirement_norm in _normalize_requirement(skill)
            for skill in social_knowledge
        ):
            verified_strengths.append(requirement)
            matched_count += 1
        else:
            critical_gaps.append(requirement)

    overall_score = round((matched_count / len(requirements)) * 100, 0) if requirements else 0
    recommendation = "APPLY" if overall_score >= 75 and not critical_gaps else "REVIEW" if overall_score >= 50 else "DO_NOT_APPLY"

    return {
        "vacancy_id": str(vacancy.get("vacancy_id", "unknown")),
        "candidate_id": str(profile.get("candidate_name", "candidate")),
        "overall_score": int(overall_score),
        "mandatory_requirements_met": matched_count,
        "mandatory_requirements_total": len(requirements),
        "evidence_coverage": round((matched_count / len(requirements)) * 100, 0) if requirements else 0,
        "critical_gaps": critical_gaps,
        "verified_strengths": verified_strengths,
        "unknowns": list(profile.get("unknowns", []) or []),
        "recommendation": recommendation,
        "explanation": (
            "La compatibilidad se calcula contra la evidencia verificable disponible y los requisitos extraídos de la vacante. "
            "Las brechas restantes requieren revisión humana antes de aprobar o rechazar."
        ),
    }

