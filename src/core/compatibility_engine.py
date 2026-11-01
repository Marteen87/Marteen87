from __future__ import annotations
from typing import Any
from src.core.evidence_registry import EvidenceRegistry

def evaluate_vacancy(vacancy: dict[str, Any], profile: dict[str, Any], registry: EvidenceRegistry) -> dict[str, Any]:
    requirements = vacancy.get("requirements", [])
    if not isinstance(requirements, list): raise ValueError("requirements must be a structured list")
    refs = set(profile.get("evidence_refs", []))
    results = []
    for req in requirements:
        if not isinstance(req, dict) or not req.get("requirement_id") or not req.get("text"):
            raise ValueError("Each requirement needs requirement_id and text")
        linked = registry.supports([x for x in req.get("evidence_refs", []) if x in refs])
        status = "VERIFIED" if linked else "INSUFFICIENT_EVIDENCE"
        results.append({"requirement_id": req["requirement_id"], "text": req["text"],
                        "type": req.get("type", "mandatory"), "status": status,
                        "evidence_ids": [e.evidence_id for e in linked],
                        "gap": None if linked else "No existe evidencia VERIFIED vinculada explícitamente."})
    mandatory = [r for r in results if r["type"] == "mandatory"]
    return {"vacancy_id": vacancy.get("vacancy_id", "unknown"), "requirements": results,
            "mandatory_total": len(mandatory),
            "mandatory_verified": sum(r["status"] == "VERIFIED" for r in mandatory),
            "critical_gaps": [r["requirement_id"] for r in mandatory if r["status"] != "VERIFIED"],
            "recommendation": "REVIEW", "human_review_required": True,
            "explanation": "El motor no aprueba candidaturas. La falta de evidencia se declara explícitamente."}
