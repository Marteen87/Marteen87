from __future__ import annotations

import base64
import json
import os
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - optional dependency
    Credentials = None  # type: ignore[assignment]
    build = None  # type: ignore[assignment]

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def build_email_message(
    vacancy: dict[str, Any],
    profile: dict[str, Any],
    matched_keywords: list[str],
    *,
    to_address: str | None = None,
) -> dict[str, str]:
    candidate_name = profile.get("candidate_name", "Candidato")
    company = vacancy.get("company", "Empresa")
    title = vacancy.get("title", "vacante")
    recipient = to_address or os.getenv("GMAIL_DRAFT_TO") or "recruiter@company.com"
    matched_text = ", ".join(matched_keywords) or "las competencias relevantes que puedan respaldarse con mi CV"

    subject = f"Interés en {title} - {company}"
    body = f"""Estimado/a equipo de selección de {company},

Me interesa la vacante de {title}. Quiero presentar mi interés en la posición y dejar constancia de mi experiencia relacionada con {matched_text}.

Mi perfil está centrado en ventas, negociación, gestión comercial, cartera, KPIs y coordinación operativa, con evidencia documentada en mi CV y en la experiencia que puedo respaldar.

Quedo a disposición para ampliar información y conversar sobre cómo podría aportar valor al equipo.

Saludos cordiales,
{candidate_name}

Nota: este es un borrador pendiente de revisión humana antes de cualquier envío.
"""
    return {"to": recipient, "subject": subject, "body": body}


def _load_gmail_credentials(credentials_path: str | Path | None, token_path: str | Path | None):
    if Credentials is None or build is None:
        raise RuntimeError(
            "Gmail dependencies are not installed. Install the project requirements first: pip install -r requirements.txt"
        )

    credential_file = Path(credentials_path or os.getenv("GMAIL_CREDENTIALS_FILE") or "credentials.json")
    token_file = Path(token_path or os.getenv("GMAIL_TOKEN_FILE") or "token.json")

    if not credential_file.exists() or not token_file.exists():
        raise RuntimeError(
            "Gmail OAuth files are missing. Create credentials.json and token.json via Google Cloud OAuth, "
            "then rerun with --gmail-draft."
        )

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds.valid:
        raise RuntimeError("The Gmail token is invalid or expired. Refresh the OAuth token and retry.")

    service = build("gmail", "v1", credentials=creds)
    return service


def create_gmail_draft(
    vacancy: dict[str, Any],
    profile: dict[str, Any],
    matched_keywords: list[str],
    *,
    credentials_path: str | Path | None = None,
    token_path: str | Path | None = None,
    to_address: str | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    message = build_email_message(vacancy, profile, matched_keywords, to_address=to_address)
    service = _load_gmail_credentials(credentials_path, token_path)

    email = EmailMessage()
    email["To"] = message["to"]
    email["Subject"] = message["subject"]
    email.set_content(message["body"])

    raw = base64.urlsafe_b64encode(email.as_bytes()).decode("ascii")
    result = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    gmail_draft_id = result.get("id")
    metadata = {
        "gmail_draft_id": gmail_draft_id,
        "gmail_draft_url": f"https://mail.google.com/mail/u/0/#drafts?compose={gmail_draft_id}",
        "status": "DRAFT_CREATED",
        "approval_required": True,
        "human_approval_required": True,
        "recipient": message["to"],
        "subject": message["subject"],
    }

    if out_dir is not None:
        drafts_dir = Path(out_dir) / "gmail_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(vacancy.get("vacancy_id", "vacancy"))).strip("-") or "vacancy"
        (drafts_dir / f"{safe_id}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return metadata
