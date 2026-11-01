from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from src.core.profile_manager import ProfileManager
from src.core.evidence_registry import EvidenceRegistry
from src.core.compatibility_engine import evaluate_vacancy
from src.core.artifact_store import ArtifactStore

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a vacancy against a local evidence-backed candidate profile.")
    parser.add_argument("--vacancy", default="tests/fixtures/puente_ai_operations_lead_2660.json")
    parser.add_argument("--profile", default="data/private/professional_profile.json")
    parser.add_argument("--evidence", default="data/private/evidence_registry.json")
    parser.add_argument("--output", default="data/applications/reviews")
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile_path, evidence_path, vacancy_path = Path(args.profile), Path(args.evidence), Path(args.vacancy)
    for required in (profile_path, evidence_path, vacancy_path):
        if not required.is_file():
            raise SystemExit(f"Required input file not found: {required}")
    manager = ProfileManager.load(profile_path)
    validation = manager.validate()
    if not validation["valid"]:
        raise SystemExit("Invalid candidate profile: " + "; ".join(validation["issues"]))
    vacancy = json.loads(vacancy_path.read_text(encoding="utf-8"))
    registry = EvidenceRegistry.from_file(evidence_path)
    result = evaluate_vacancy(vacancy, manager.profile.to_dict(), registry)
    provenance = {
        "vacancy_source_url": vacancy.get("source_url", ""),
        "vacancy_fixture_status": vacancy.get("fixture_status", "UNSPECIFIED"),
        "vacancy_file": str(vacancy_path),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "profile_file": str(profile_path),
        "evidence_file": str(evidence_path),
        "policy": "HUMAN_REVIEW_REQUIRED_NO_AUTOMATIC_APPLICATION"
    }
    store = ArtifactStore(args.output)
    artifact_name = vacancy.get("vacancy_id", "vacancy-review")
    saved = store.save_json(artifact_name, result, provenance)
    gaps = ", ".join(result["critical_gaps"]) or "none"
    markdown = (
        f"# Vacancy review: {artifact_name}\n\n"
        f"- Recommendation: **{result['recommendation']}**\n"
        f"- Mandatory requirements verified: {result['mandatory_verified']}/{result['mandatory_total']}\n"
        f"- Critical evidence gaps: {gaps}\n"
        f"- Human review required: **yes**\n\n"
        "This is an evidence-coverage review, not a hiring probability or an automatic apply decision.\n"
    )
    store.save_markdown(artifact_name, markdown, provenance)
    print(f"Review saved: {Path(args.output) / artifact_name}")
    print(f"Recommendation: {result['recommendation']} | Mandatory verified: {result['mandatory_verified']}/{result['mandatory_total']}")
    print(f"Critical gaps: {gaps}")
    print(f"SHA-256: {saved['hash_sha256']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
