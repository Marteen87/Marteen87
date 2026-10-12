"""Evidence-first vacancy triage. Never submits applications."""
from __future__ import annotations
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "vacancy_id", "company", "title", "location", "work_mode", "url",
    "description", "requirements", "salary", "source", "posted_date"
}
STOPWORDS = {
    "para", "con", "por", "una", "uno", "del", "las", "los", "que", "como",
    "the", "and", "for", "with", "from", "you", "your", "our", "are", "will",
    "una", "sobre", "entre", "tener", "ser", "más", "mas", "experiencia"
}

def terms(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-záéíóúüñ0-9+#.]{3,}", (value or "").lower())
            if t not in STOPWORDS}

def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def read_vacancies(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError("CSV missing required columns: " + ", ".join(sorted(missing)))
        rows = []
        for row in reader:
            row = {k: (v or "").strip() for k, v in row.items()}
            if row.get("vacancy_id") and row.get("title") and row.get("company"):
                rows.append(row)
        ids = [r["vacancy_id"] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("vacancy_id values must be unique")
        return rows

def score_vacancy(vacancy: dict[str, str], profile: dict[str, Any]) -> dict[str, Any]:
    """Transparent lexical overlap against only verified profile keywords."""
    target = terms(" ".join([
        vacancy.get("title", ""), vacancy.get("description", ""),
        vacancy.get("requirements", "")
    ]))
    skills = profile.get("verified_keywords", [])
    verified = {str(x).strip().lower() for x in skills if str(x).strip()}
    matched = sorted(k for k in verified if terms(k) and terms(k).issubset(target))
    gaps = sorted(k for k in verified if k not in matched)
    score = round(100 * len(matched) / len(verified)) if verified else 0
    return {
        "match_score": score,
        "matched_verified_keywords": matched,
        "other_profile_keywords_not_found": gaps,
        "score_method": "matched verified keywords / all verified keywords; lexical heuristic",
        "approval_status": "REVIEW_REQUIRED",
        "warning": "This score is not a hiring probability; validate each requirement manually."
    }

def build_pack(v: dict[str, str], profile: dict[str, Any], result: dict[str, Any]) -> str:
    name = profile.get("candidate_name", "Candidato")
    evidence = profile.get("evidence", [])
    evidence_lines = "\n".join(f"- {e}" for e in evidence) or "- Pendiente de completar con evidencia verificada del CV."
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
- Confirmar que cada requisito que se mencione está respaldado por el CV.
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

def run(profile_path: Path, vacancies_path: Path, out_dir: Path) -> dict[str, Any]:
    profile = load_json(profile_path)
    vacancies = read_vacancies(vacancies_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    packs_dir = out_dir / "applications"
    packs_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for v in vacancies:
        result = {**v, **score_vacancy(v, profile)}
        results.append(result)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", v["vacancy_id"]).strip("-") or "vacancy"
        (packs_dir / f"{safe_id}.md").write_text(build_pack(v, profile, result), encoding="utf-8")
    results.sort(key=lambda x: (-x["match_score"], x["company"], x["title"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vacancies_processed": len(results),
        "applications_sent": 0,
        "human_approval_required": True,
        "results": results
    }
    (out_dir / "triage.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Informe de vacantes", "", f"Procesadas: {len(results)}", "Envíos realizados: 0", "",
             "| Match | Empresa | Puesto | Modalidad | Estado | URL |",
             "|---:|---|---|---|---|---|"]
    for r in results:
        url = r.get("url", "").replace("|", "%7C")
        lines.append(f"| {r['match_score']}% | {r['company']} | {r['title']} | {r.get('work_mode','')} | REVISIÓN HUMANA | {url} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=Path("data/profile.json"))
    parser.add_argument("--vacancies", type=Path, default=Path("data/vacancies.csv"))
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()
    payload = run(args.profile, args.vacancies, args.out)
    print(f"Processed {payload['vacancies_processed']} vacancies; applications sent: 0.")

if __name__ == "__main__":
    main()
