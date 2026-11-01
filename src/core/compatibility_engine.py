from __future__ import annotations
from typing import Any
from src.core.evidence_registry import EvidenceRegistry

VALID_REQUIREMENT_TYPES = {"mandatory", "desirable"}

def evaluate_vacancy(vacancy: dict[str, Any], profile: dict[str, Any], registry: EvidenceRegistry) -> dict[str, Any]:
    requirements = vacancy.get("requirements", [])
    if not isinstance(requirements, list):
        raise ValueError("requirements must be a structured list")
    profile_refs = profile.get("evidence_refs", [])
    if not isinstance(profile_refs, list) or not all(isinstance(x, str) and x.strip() for x in profile_refs):
        raise ValueError("profile evidence_refs must be a list of non-empty evidence IDs")
    results = []
    seen_ids = set()
    for req in requirements:
        if not isinstance(req, dict) or not req.get("requirement_id") or not req.get("text"):
            raise ValueError("Each requirement needs requirement_id and text")
        requirement_id = req["requirement_id"]
        if requirement_id in seen_ids:
            raise ValueError(f"Duplicate requirement_id: {requirement_id}")
        seen_ids.add(requirement_id)
        requirement_type = req.get("type", "mandatory")
        if requirement_type not in VALID_REQUIREMENT_TYPES:
            raise ValueError(f"Invalid requirement type for {requirement_id}: {requirement_type}")
        # Candidate evidence belongs to the private profile/registry, not the public vacancy fixture.
        # The registry itself enforces VERIFIED status and reviewed requirement mapping.
        linked = registry.supports(profile_refs, requirement_id)
        status = "VERIFIED" if linked else "INSUFFICIENT_EVIDENCE"
        results.append({
            "requirement_id": requirement_id,
            "text": req["text"],
            "type": requirement_type,
            "status": status,
            "evidence_ids": [e.evidence_id for e in linked],
            "gap": None if linked else "No existe evidencia VERIFIED revisada y vinculada explícitamente a este requisito."
        })
    mandatory = [r for r in results if r["type"] == "mandatory"]
    return {
        "vacancy_id": vacancy.get("vacancy_id", "unknown"),
        "requirements": results,
        "mandatory_total": len(mandatory),
        "mandatory_verified": sum(r["status"] == "VERIFIED" for r in mandatory),
        "critical_gaps": [r["requirement_id"] for r in mandatory if r["status"] != "VERIFIED"],
        "recommendation": "REVIEW",
        "human_review_required": True,
        "explanation": "La autenticidad de una evidencia no demuestra por sí sola su pertinencia; cada vínculo requiere revisión explícita. El motor no aprueba candidaturas."
    }
