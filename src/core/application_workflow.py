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

def _verify_integrity(payload: dict[str, Any]) -> None:
    expected = payload.get("integrity_sha256")
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    if not expected or expected != _sha256(unsigned):
        raise ApplicationWorkflowError("Application pack integrity check failed; review the source artifact.")


def _as_lines(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item) for item in value]
    if isinstance(value, dict):
        return [f"{key}: {json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else item}" for key, item in value.items()]
    return [str(value)]

def _relevance(text: str, requirements: list[dict[str, Any]]) -> int:
    # Presentation order only; this lexical score is never treated as evidence or compatibility.
    words = set(re.findall(r"[a-z0-9áéíóúñ]{3,}", text.lower()))
    target = set(re.findall(
        r"[a-z0-9áéíóúñ]{3,}",
        " ".join(str(item.get("text", "")) for item in requirements).lower()
    ))
    return len(words & target)

def _render_tailored_cv(profile: dict[str, Any], vacancy: dict[str, Any]) -> str:
    sections = [f"# {profile.get('candidate_name', '')}"]
    if profile.get("headline"):
        sections.extend(["", f"**{profile['headline']}**"])
    if profile.get("location"):
        sections.extend(["", str(profile["location"])])
    contact = profile.get("contact")
    if contact:
        sections.extend(["", " | ".join(_as_lines(contact))])
    if profile.get("summary"):
        sections.extend(["", "## Perfil profesional", str(profile["summary"])])
    requirements = vacancy.get("requirements", [])
    for field, heading in (
        ("skills", "Competencias"),
        ("experience", "Experiencia"),
        ("employment_history", "Trayectoria profesional"),
        ("projects", "Proyectos"),
        ("education", "Formación"),
        ("certifications", "Capacitaciones y certificaciones"),
        ("languages", "Idiomas"),
    ):
        entries = _as_lines(profile.get(field))
        if not entries:
            continue
        if field in {"skills", "experience", "employment_history", "projects"}:
            entries.sort(key=lambda item: _relevance(item, requirements), reverse=True)
        sections.extend(["", f"## {heading}"])
        sections.extend(f"- {item}" for item in entries)
    sections.extend([
        "",
        "---",
        f"**Objetivo de esta versión:** {vacancy.get('title', '')} — {vacancy.get('company', '')}.",
        "El orden de presentación se ajustó a los términos de la vacante. Las afirmaciones se copiaron del perfil; el orden léxico no constituye prueba de experiencia.",
    ])
    return "\n".join(sections) + "\n"

def _render_cover_letter(profile: dict[str, Any], vacancy: dict[str, Any], evaluation: dict[str, Any]) -> str:
    name = str(profile.get("candidate_name", "")).strip()
    headline = str(profile.get("headline", "")).strip()
    summary = str(profile.get("summary", "")).strip()
    verified = [
        item for item in evaluation.get("requirements", [])
        if item.get("status") == "VERIFIED" and item.get("evidence_ids")
    ]
    lines = [
        f"# Carta de presentación — {vacancy.get('title', '')}",
        "",
        f"Estimado equipo de selección de {vacancy.get('company', '')}:",
        "",
        f"Me interesa presentar mi candidatura para la posición de {vacancy.get('title', '')}.",
    ]
    if headline:
        lines.extend(["", f"Mi perfil profesional está orientado a {headline}."])
    if summary:
        lines.extend(["", summary])
    if verified:
        lines.extend(["", "Entre los requisitos para los que existe evidencia revisada y vinculada se encuentran:"])
        lines.extend(f"- {item['text']} (evidencia: {', '.join(item['evidence_ids'])})" for item in verified)
    else:
        lines.extend([
            "",
            "Quedo a disposición para conversar sobre las necesidades del puesto y ampliar los antecedentes de mi trayectoria que resulten pertinentes.",
        ])
    lines.extend(["", "Saludos cordiales,", "", name, "", "---", "Borrador personalizado pendiente de revisión humana. No enviar sin verificar todos los datos y completar los campos que correspondan."])
    return "\n".join(lines) + "\n"

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
    (folder / "tailored_cv.md").write_text(_render_tailored_cv(snapshot, vacancy), encoding="utf-8")
    (folder / "cover_letter.md").write_text(_render_cover_letter(snapshot, vacancy, evaluation), encoding="utf-8")

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
        "```json",
        *json.dumps(snapshot, ensure_ascii=False, indent=2).splitlines(),
        "```",
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
    (folder / "application.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
    _verify_integrity(payload)
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
    _verify_integrity(payload)
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
