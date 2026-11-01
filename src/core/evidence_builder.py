from __future__ import annotations

from typing import Any

ARTIFACT_GUIDANCE = {
    "employment": [
        "CV chronology with month/year start and end dates",
        "Employment certificate, contract, payslip, or reference (redact sensitive data)",
        "A concise description of role, responsibilities, scope, and reporting line",
    ],
    "automation": [
        "Sanitized workflow diagram or repository commit",
        "Configuration/export with secrets and personal data removed",
        "Execution logs, tests, or screenshots showing a real run",
        "Evidence that the workflow remained active after initial delivery",
        "User/team scope and operating dates",
    ],
    "commercial": [
        "Sanitized CRM/export, pipeline report, proposal, or account plan",
        "Documented responsibilities in prospecting, negotiation, closing, or account growth",
        "Period, customer segment, deal size, and outcome where independently supportable",
    ],
    "education": [
        "Diploma, certificate, transcript, or institution-issued record",
        "Institution, program name, completion date, and status",
    ],
    "technical": [
        "Code sample or repository commit attributable to the candidate",
        "Reproducible test, API request/response, or experiment log",
        "Exact tools used, personal contribution, and execution environment",
    ],
    "general": [
        "Original source document or artifact with date and provenance",
        "A short explanation of what the artifact proves and what it does not prove",
    ],
}


def _guidance(record: Any) -> tuple[str, list[str]]:
    text = f"{getattr(record, 'evidence_id', '')} {getattr(record, 'claim', '')}".lower()
    if any(token in text for token in ("employment", "years", "operations", "supervisor", "experience", "work history")):
        return "employment", ARTIFACT_GUIDANCE["employment"]
    if any(token in text for token in ("automation", "workflow", "organism", "llm", "api", "agent", "python", "script", "technical")):
        return "automation_or_technical", ARTIFACT_GUIDANCE["automation"] + ARTIFACT_GUIDANCE["technical"]
    if any(token in text for token in ("commercial", "sales", "b2b", "account", "negotiat", "pipeline", "prospect", "automotive", "credit", "financial")):
        return "commercial", ARTIFACT_GUIDANCE["commercial"]
    if any(token in text for token in ("education", "degree", "mercantil", "course", "training", "certificate")):
        return "education", ARTIFACT_GUIDANCE["education"]
    return "general", ARTIFACT_GUIDANCE["general"]


def build_collection_plan(profile: dict[str, Any], registry: Any) -> dict[str, Any]:
    """Build a human-operated evidence collection plan without changing evidence status."""
    refs = profile.get("evidence_refs", [])
    if not isinstance(refs, list) or not all(isinstance(x, str) and x.strip() for x in refs):
        raise ValueError("profile evidence_refs must be a list of non-empty evidence IDs")

    items = []
    missing_refs = []
    for evidence_id in refs:
        record = registry.get_by_id(evidence_id)
        if record is None:
            missing_refs.append(evidence_id)
            items.append({
                "evidence_id": evidence_id,
                "claim": None,
                "current_status": "MISSING_RECORD",
                "collection_status": "ACTION_REQUIRED",
                "category": "general",
                "recommended_artifacts": ARTIFACT_GUIDANCE["general"],
                "review_checklist": [
                    "Locate the original source or remove the unsupported reference from the private profile",
                    "Record source, date, and provenance",
                    "Do not describe this claim as verified until a reviewer checks the source",
                ],
                "status_change": "PROHIBITED_AUTOMATICALLY",
            })
            continue

        category, artifacts = _guidance(record)
        current_status = record.status
        items.append({
            "evidence_id": record.evidence_id,
            "claim": record.claim,
            "current_status": current_status,
            "collection_status": "READY_FOR_HUMAN_COLLECTION" if current_status != "VERIFIED" else "VERIFY_SCOPE_AND_MAPPING",
            "category": category,
            "source_recorded": bool(record.source.strip()),
            "source_url_recorded": bool(record.source_url.strip()),
            "recommended_artifacts": artifacts,
            "review_checklist": [
                "Check that the artifact is authentic, attributable, dated, and readable",
                "Redact passwords, tokens, personal data, confidential client data, and commercially sensitive details",
                "Record exactly which part of the claim the artifact supports",
                "Separate direct personal contribution from team or product capability",
                "Map to a vacancy requirement only after a human reviewer assesses relevance",
                "Record reviewer identity and timestamp for every approved requirement mapping",
            ],
            "status_change": "REQUIRES_HUMAN_VERIFICATION",
        })

    return {
        "schema_version": "1.0",
        "candidate_id": profile.get("candidate_id", "candidate-local"),
        "plan_type": "EVIDENCE_COLLECTION",
        "evidence_items": items,
        "missing_registry_records": missing_refs,
        "summary": {
            "referenced_evidence": len(refs),
            "records_found": len(refs) - len(missing_refs),
            "records_missing": len(missing_refs),
            "verified_records_not_reverified": sum(
                1 for item in items if item["current_status"] == "VERIFIED"
            ),
            "automatic_verification_performed": False,
        },
        "guardrails": [
            "This plan does not verify evidence or change registry status.",
            "SELF_REPORTED, PARTIAL, UNKNOWN, and SYNTHETIC records do not become VERIFIED by inclusion in this plan.",
            "Evidence authenticity and relevance to a specific requirement are separate review decisions.",
            "Never upload private candidate evidence to a public repository.",
        ],
    }
