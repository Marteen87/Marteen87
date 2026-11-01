from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gmail_draft import build_email_message, create_gmail_draft

REQUIRED_COLUMNS = {
    "vacancy_id",
    "company",
    "title",
    "location",
    "work_mode",
    "url",
    "description",
    "requirements",
    "salary",
    "source",
    "posted_date",
}

STOPWORDS = {
    "para",
    "con",
    "por",
    "una",
    "uno",
    "del",
    "las",
    "los",
    "que",
    "como",
    "the",
    "and",
    "for",
    "with",
    "from",
    "you",
    "your",
    "our",
    "are",
    "will",
    "sobre",
    "entre",
    "tener",
    "ser",
    "más",
    "mas",
    "experiencia",
    "de",
    "en",
    "el",
    "la",
    "al",
    "un",
    "una",
    "y",
    "o",
    "se",
    "somos",
    "buscamos",
    "requerimientos",
    "required",
    "skills",
    "responsibilities",
    "must",
    "role",
}

ALIASES = {
    "ventas": {"ventas", "venta", "vendedor", "ejecutivo de ventas", "sales"},
    "asesoría comercial": {"asesoria comercial", "asesor comercial", "asesoramiento comercial", "consultoria comercial"},
    "negociación": {"negociacion", "negociaciones", "negociacion comercial"},
    "prospección": {"prospeccion", "prospectacion", "prospeccion comercial"},
    "gestión de cartera": {"gestion de cartera", "cartera", "portafolio de clientes"},
    "embudo de ventas": {"embudo de ventas", "funnel de ventas", "funnels de ventas"},
    "presupuestos": {"presupuestos", "cotizaciones", "presupuesto", "cotizacion"},
    "cotizaciones": {"cotizaciones", "cotizacion"},
    "análisis financiero": {"analisis financiero", "analisis de finanzas", "analisis financiero comercial"},
    "créditos": {"creditos", "credito", "crédito"},
    "análisis de riesgo": {"analisis de riesgo", "analisis riesgos", "riesgo comercial"},
    "supervisión operativa": {"supervision operativa", "supervisión operativa", "operaciones"},
    "liderazgo": {"liderazgo", "liderar", "lider"},
    "capacitación de equipos": {"capacitacion de equipos", "formacion de equipos", "capacitación de vendedores"},
    "indicadores de gestión": {"indicadores de gestion", "kpis", "dashboard"},
    "KPIs": {"kpis", "indicadores clave", "dashboards"},
    "automatización de marketing": {"automatizacion de marketing", "automatizacion marketing", "marketing automation"},
    "inteligencia artificial": {"inteligencia artificial", "ia", "ai", "artificial intelligence"},
    "generación de leads": {"generacion de leads", "lead generation", "generacion de contactos"},
    "prospección omnicanal": {"prospeccion omnicanal", "omnichannel sales", "prospeccion multicanal"},
    "Excel": {"excel", "microsoft excel", "hojas de calculo"},
    "SAP": {"sap"},
    "Office": {"office", "microsoft office"},
    "inglés avanzado": {"ingles avanzado", "english advanced", "inglés alto"},
    "sector automotriz": {"sector automotriz", "automotriz"},
    "sector inmobiliario": {"sector inmobiliario", "inmobiliario"},
    "grandes cuentas": {"grandes cuentas", "key accounts", "cuentas clave"},
    "B2B": {"b2b", "business to business"},
    "B2C": {"b2c", "business to consumer"},
    "planes de ahorro": {"planes de ahorro", "ahorro"},
    "coordinación operativa": {"coordinacion operativa", "coordinacion", "operaciones"},
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " y ")
    text = text.replace("+", " ")
    text = re.sub(r"[^a-z0-9#\s-]", " ", text)
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.]{3,}", normalize_text(value))
        if token not in STOPWORDS and len(token) >= 3
    }


def keyword_matches(skill: str, target_text: str) -> bool:
    normalized_skill = normalize_text(skill)
    if not normalized_skill:
        return False

    variants = {normalized_skill} | {
        normalize_text(item)
        for item in ALIASES.get(skill.strip().lower(), {skill.strip().lower()})
    }
    haystack = normalize_text(target_text)

    for variant in variants:
        if not variant:
            continue
        if variant in haystack:
            return True

        variant_tokens = set(variant.split())
        haystack_tokens = set(haystack.split())
        if variant_tokens and variant_tokens.issubset(haystack_tokens):
            return True

        if len(variant_tokens) > 1:
            score = sum(1 for token in variant_tokens if token in haystack_tokens)
            if score >= max(1, len(variant_tokens) - 1):
                return True

    return False


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_vacancies(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        rows: list[dict[str, str]] = []
        for row in reader:
            row = {key: (value or "").strip() for key, value in row.items()}
            if row.get("vacancy_id") and row.get("title") and row.get("company"):
                rows.append(row)

        ids = [row["vacancy_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("vacancy_id values must be unique")

        return rows


def score_vacancy(vacancy: dict[str, str], profile: dict[str, Any]) -> dict[str, Any]:
    target = " ".join(
        [
            vacancy.get("title", ""),
            vacancy.get("description", ""),
            vacancy.get("requirements", ""),
        ]
    )
    skills = profile.get("verified_keywords", [])
    verified = [str(item).strip() for item in skills if str(item).strip()]
    matched = sorted(skill for skill in verified if keyword_matches(skill, target))
    gaps = sorted(skill for skill in verified if skill not in matched)
    score = round(100 * len(matched) / len(verified)) if verified else 0
    return {
        "match_score": score,
        "matched_verified_keywords": matched,
        "other_profile_keywords_not_found": gaps,
        "score_method": "matched verified keywords / all verified keywords; lexical heuristic with normalization and alias support",
        "approval_status": "REVIEW_REQUIRED",
        "warning": "This score is not a hiring probability; validate each requirement manually.",
    }


def build_pack(v: dict[str, str], profile: dict[str, Any], result: dict[str, Any]) -> str:
    name = profile.get("candidate_name", "Candidato")
    evidence = profile.get("evidence", [])
    evidence_lines = "\n".join(f"- {item}" for item in evidence) or "- Pendiente de completar con evidencia verificada del CV."
    matched = ", ".join(result["matched_verified_keywords"]) or "Sin coincidencias verificadas detectadas"

    return f"""# Borrador de postulación — {v['company']} / {v['title']}

- Vacante: {v.get('url') or 'URL pendiente'}
- Ubicación/modalidad: {v.get('location', '')} / {v.get('work_mode', '')}
- Fuente: {v.get('source', '')}
- Fecha publicada (si informada): {v.get('posted_date', '')}
- Match heurístico: {result['match_score']}%
- Estado: **REVISIÓN HUMANA OBLIGATORIA — NO ENVIADO**

## Coincidencias detectadas
{matched}

## Evidencia disponible del perfil
{evidence_lines}

## Brechas y verificaciones pendientes
- Confirmar requisitos excluyentes, idioma, modalidad, horario y remuneración.
- Confirmar que cada requisito que se mencione esté respaldado por el CV.
- No se detectan automáticamente equivalencias semánticas ni experiencia no documentada.

## Mensaje de presentación — BORRADOR
Hola, equipo de selección de {v['company']}:

Me interesa la posición de {v['title']}. Mi experiencia y las competencias que puedo respaldar en mi CV incluyen: {matched}.

Quedo a disposición para ampliar la información y conversar sobre cómo podría contribuir al equipo.

Saludos,
{name}

---
**Control:** revisar y editar este borrador antes de cualquier uso. No se envió ninguna postulación.
"""


def run(
    profile_path: Path,
    vacancies_path: Path,
    out_dir: Path,
    *,
    gmail_draft: bool = False,
    gmail_to: str | None = None,
    gmail_credentials: Path | None = None,
    gmail_token: Path | None = None,
) -> dict[str, Any]:
    profile = load_json(profile_path)
    vacancies = read_vacancies(vacancies_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    packs_dir = out_dir / "applications"
    packs_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for vacancy in vacancies:
        result = {**vacancy, **score_vacancy(vacancy, profile)}
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", vacancy["vacancy_id"]).strip("-") or "vacancy"
        (packs_dir / f"{safe_id}.md").write_text(build_pack(vacancy, profile, result), encoding="utf-8")

        if gmail_draft:
            try:
                draft_message = build_email_message(vacancy, profile, result["matched_verified_keywords"], to_address=gmail_to)
                draft_metadata = create_gmail_draft(
                    vacancy,
                    profile,
                    result["matched_verified_keywords"],
                    credentials_path=gmail_credentials,
                    token_path=gmail_token,
                    to_address=gmail_to,
                    out_dir=out_dir,
                )
                result["gmail_draft_status"] = draft_metadata.get("status", "DRAFT_CREATED")
                result["gmail_draft_id"] = draft_metadata.get("gmail_draft_id")
                result["gmail_draft_url"] = draft_metadata.get("gmail_draft_url")
                result["gmail_message"] = draft_message
            except Exception as exc:  # pragma: no cover - integrates with external service
                result["gmail_draft_status"] = "FAILED"
                result["gmail_draft_error"] = str(exc)

        results.append(result)

    results.sort(key=lambda item: (-item["match_score"], item["company"], item["title"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vacancies_processed": len(results),
        "applications_sent": 0,
        "human_approval_required": True,
        "gmail_draft_enabled": gmail_draft,
        "results": results,
    }

    (out_dir / "triage.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Informe de vacantes",
        "",
        f"Procesadas: {len(results)}",
        "Envíos realizados: 0",
        "",
        "| Match | Empresa | Puesto | Modalidad | Estado | URL |",
        "|---:|---|---|---|---|---|",
    ]

    for entry in results:
        url = entry.get("url", "").replace("|", "%7C")
        draft_state = entry.get("gmail_draft_status", "PENDING")
        lines.append(f"| {entry['match_score']}% | {entry['company']} | {entry['title']} | {entry.get('work_mode', '')} | {draft_state} | {url} |")

    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first vacancy triage. Drafts are reviewable but never auto-sent.")
    parser.add_argument("--profile", type=Path, default=Path("data/profile.json"))
    parser.add_argument("--vacancies", type=Path, default=Path("data/vacancies.csv"))
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--gmail-draft", action="store_true", help="Create Gmail drafts instead of only local markdown packs.")
    parser.add_argument("--gmail-to", default=os.getenv("GMAIL_DRAFT_TO"), help="Recipient address for the Gmail draft.")
    parser.add_argument("--gmail-credentials", type=Path, default=Path(os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")), help="Path to the Gmail OAuth credentials JSON file.")
    parser.add_argument("--gmail-token", type=Path, default=Path(os.getenv("GMAIL_TOKEN_FILE", "token.json")), help="Path to the Gmail OAuth token JSON file.")
    args = parser.parse_args()

    payload = run(
        args.profile,
        args.vacancies,
        args.out,
        gmail_draft=args.gmail_draft,
        gmail_to=args.gmail_to,
        gmail_credentials=args.gmail_credentials,
        gmail_token=args.gmail_token,
    )
    print(f"Processed {payload['vacancies_processed']} vacancies; applications sent: 0.")


if __name__ == "__main__":
    main()









































































































































































































































































