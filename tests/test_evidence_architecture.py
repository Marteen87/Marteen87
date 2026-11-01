import json
from pathlib import Path
import tempfile
import unittest

from src.core.artifact_store import ArtifactStore
from src.core.compatibility_engine import evaluate_vacancy
from src.core.evidence_registry import DEFAULT_REGISTRY, EvidenceRegistry
from src.core.profile_manager import CandidateProfile, ProfileManager
from src.core.similarity_service import SimilarityIndex


class EvidenceArchitectureTests(unittest.TestCase):
    def test_profile_manager_validates_template(self):
        profile = CandidateProfile(
            candidate_name="Test User",
            verified_skills=["ventas", "excel"],
            verified_experience=["ventas B2B"],
            unknowns=[],
            constraints=["no inventar evidencia"],
            evidence_refs=[],
        )
        manager = ProfileManager(profile=profile)
        validation = manager.validate()
        self.assertTrue(validation["valid"])

    def test_evidence_registry_supports_verified_claims(self):
        registry = EvidenceRegistry(DEFAULT_REGISTRY)
        supports = registry.supports_claim("ventas B2B")
        self.assertTrue(any(record.evidence_id == "EV-001" for record in supports))

    def test_compatibility_engine_uses_evidence(self):
        profile = {
            "candidate_name": "Test User",
            "verified_skills": ["ventas", "excel", "gestión de cartera"],
            "verified_experience": ["ventas B2B"],
            "unknowns": ["python avanzado"],
        }
        vacancy = {
            "vacancy_id": "V-100",
            "title": "Asesor comercial",
            "requirements": "ventas; gestión de cartera; excel; B2B",
            "description": "Necesitamos alguien con experiencia comercial y manejo de cartera.",
        }
        result = evaluate_vacancy(vacancy, profile, EvidenceRegistry(DEFAULT_REGISTRY))
        self.assertGreater(result["overall_score"], 60)
        self.assertEqual(result["recommendation"], "APPLY")

    def test_similarity_index_tracks_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SimilarityIndex(Path(tmpdir) / "similarity.json")
            artifact_id = "draft-001"
            record = store.register(artifact_id, "ventas B2B gestión de cartera", metadata={"preview": "ventas B2B gestión de cartera"})
            self.assertEqual(record["artifact_id"], artifact_id)
            self.assertTrue(store.find_similar("ventas B2B gestión de cartera"))

    def test_artifact_store_writes_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(Path(tmpdir) / "artifacts")
            payload = store.save_json("vacancy-01", {"status": "PENDING"}, provenance={"source": "manual-review"})
            self.assertIn("hash_sha256", payload)


if __name__ == "__main__":
    unittest.main()

