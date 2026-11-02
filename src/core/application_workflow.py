from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.core.compatibility_engine import evaluate_vacancy
from src.core.evidence_registry import EvidenceRegistry

SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}$")
PROFILE_FIELDS = (
    "candidate_id", "candidate_name", "headline", "summary", "location",
    "contact", "role_focus", "skills", "experience", "employment_history",
    "education", "languages", "projects", "certifications", "portfolio_url",
)

class ApplicationWorkflowError(ValueError):
    pass

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _safe_id(value: Any) -> str:
    text = str(value or "").strip()
    if not SAFE_ID.fullmatch(text):
        raise ApplicationWorkflowError("vacancy_id must be a safe identifier (letters, numbers, '_' or '-').")
    return text

def _is_real_https_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and bool(host) and host not in {
            "example.com", "www.example.com", "example.invalid", "localhost"
        } and "." in host
    except ValueError:
        return False

def validate_vacancy_for_application(vacancy: dict[str, Any]) -> None:
    if not isinstance(vacancy, dict):
        raise ApplicationWorkflowError("Vacancy must be an object.")
    _safe_id(vacancy.get("vacancy_id"))
    for field in ("title", "company"):
        if not str(vacancy.get(field) or "").strip():
            raise ApplicationWorkflowError(f"Vacancy field '{field}' is required.")
    if str(vacancy.get("verification_status") or "").upper() != "VERIFIED":
        raise ApplicationWorkflowError("Vacancy is blocked: verification_status must be VERIFIED.")
    if not _is_real_https_url(vacancy.get("source_url")):
        raise ApplicationWorkflowError("Vacancy is blocked: a real HTTPS source_url is required.")
    if not str(vacancy.get("source_verified_by") or "").strip():
        raise ApplicationWorkflowError("Vacancy is blocked: source_verified_by is required.")
    if not str(vacancy.get("source_verified_at") or "").strip():
        raise ApplicationWorkflowError("Vacancy is blocked: source_verified_at is required.")
    requirements = vacancy.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ApplicationWorkflowError("Vacancy must contain a non-empty structured requirements list.")

def _profile_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    # Only candidate-supplied profile fields are copied. No claims are inferred or generated.
    return {key: profile[key] for key in PROFILE_FIELDS if key in profile}

def _sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def prepare_application(
    vacancy: dict[str, Any],
    profile: dict[str, Any],
    registry: EvidenceRegistry,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Prepare a traceable application pack. This function never approves or submits."""
    validate_vacancy_for_application(vacancy)
    if not isinstance(profile, dict) or not str(profile.get("candidate_id") or "").strip():
        raise ApplicationWorkflowError("A valid private candidate profile is required.")

    evaluation = evaluate_vacancy(vacancy, profile, registry)
    snapshot = _profile_snapshot(profile)
    if not snapshot.get("candidate_name"):
        raise ApplicationWorkflowError("candidate_name is required before generating a candidate-facing pack.")

    application_id = _safe_id(vacancy["vacancy_id"])
    created_at = _now()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "application_id": application_id,
        "status": "PREPARED_PENDING_HUMAN_APPROVAL",
        "created_at": created_at,
        "vacancy": {
            "vacancy_id": application_id,
            "title": vacancy["title"],
            "company": vacancy["company"],
            "source_url": vacancy["source_url"],
            "source_verified_by": vacancy["source_verified_by"],
            "source_verified_at": vacancy["source_verified_at"],
            "location": vacancy.get("location", ""),
            "work_mode": vacancy.get("work_mode", ""),
        },
        "candidate_snapshot": snapshot,
        "evaluation": evaluation,
        "requirement_trace": evaluation["requirements"],
        "human_decision": None,
        "submission": None,
        "guardrails": [
            "Prepared content only; no email, portal form, or application was submitted.",
            "Candidate claims are copied only from the private profile snapshot.",
            "Only VERIFIED evidence explicitly mapped to a requirement counts as verified support.",
            "Human approval is mandatory before any external submission.",
        ],
    }
    payload["integrity_sha256"] = _sha256(payload)

    folder = Path(output_dir) / application_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "application.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )

    lines = [
        f"# Application pack — {vacancy['title']} / {vacancy['company']}",
        "",
        f"- Status: **{payload['status']}**",
        f"- Vacancy source: {vacancy['source_url']}",
        f"- Candidate: {snapshot['candidate_name']}",
        f"- Evidence coverage: {evaluation['mandatory_verified']}/{evaluation['mandatory_total']} mandatory requirements verified",
        "- Submission: **NOT SENT**",
        "",
        "## Candidate profile snapshot",
        "The following fields are copied from the private candidate profile; review and edit before use.",
        "",
        "    " + json.dumps(snapshot, ensure_ascii=False, indent=2).replace("\\n", "\\n    "),
        "",
        "## Requirement-by-requirement review",
    ]
    for item in evaluation["requirements"]:
        lines.extend([
            f"- **{item['requirement_id']} — {item['type']} — {item['status']}**: {item['text']}",
            f"  - Evidence IDs: {', '.join(item['evidence_ids']) or 'none'}",
            f"  - Gap: {item['gap'] or 'none'}",
        ])
    lines.extend([
        "",
        "## Human review",
        "Approval is not implied by this pack. Record an explicit reviewer decision before submission.",
        "",
        f"- Integrity SHA-256: {payload['integrity_sha256']}",
    ])
    (folder / "application.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return payload

def record_human_decision(
    application_file: str | Path,
    *,
    decision: str,
    reviewer: str,
    notes: str = "",
    decided_at: str | None = None,
) -> dict[str, Any]:
    path = Path(application_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PREPARED_PENDING_HUMAN_APPROVAL":
        raise ApplicationWorkflowError("Human decision can only be recorded for a pending application.")
    normalized = decision.strip().upper()
    if normalized not in {"APPROVE", "REJECT"}:
        raise ApplicationWorkflowError("decision must be APPROVE or REJECT.")
    if not reviewer.strip():
        raise ApplicationWorkflowError("A human reviewer identity is required.")
    payload["human_decision"] = {
        "decision": normalized,
        "reviewer": reviewer.strip(),
        "decided_at": decided_at or _now(),
        "notes": notes,
    }
    payload["status"] = "APPROVED_READY_TO_SUBMIT" if normalized == "APPROVE" else "REJECTED_BY_HUMAN"
    payload.pop("integrity_sha256", None)
    payload["integrity_sha256"] = _sha256(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload

def record_confirmed_submission(
    application_file: str | Path,
    *,
    channel: str,
    confirmation_reference: str,
    reviewer: str,
    submitted_at: str | None = None,
) -> dict[str, Any]:
    """Record a submission already completed externally; it does not perform the submission."""
    path = Path(application_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "APPROVED_READY_TO_SUBMIT":
        raise ApplicationWorkflowError("Submission cannot be recorded before explicit human approval.")
    if not channel.strip() or not confirmation_reference.strip() or not reviewer.strip():
        raise ApplicationWorkflowError("Channel, external confirmation reference, and reviewer are required.")
    payload["submission"] = {
        "status": "SUBMITTED_CONFIRMED",
        "channel": channel.strip(),
        "confirmation_reference": confirmation_reference.strip(),
        "confirmed_by": reviewer.strip(),
        "submitted_at": submitted_at or _now(),
    }
    payload["status"] = "SUBMITTED_CONFIRMED"
    payload.pop("integrity_sha256", None)
    payload["integrity_sha256"] = _sha256(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload
