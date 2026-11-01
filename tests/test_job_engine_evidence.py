import json, tempfile, unittest
from pathlib import Path
from src.core.profile_manager import CandidateProfile, ProfileManager
from src.core.evidence_registry import EvidenceRecord, EvidenceRegistry
from src.core.compatibility_engine import evaluate_vacancy
from src.core.artifact_store import ArtifactStore
from src.core.similarity_service import SimilarityIndex
from src.core.review_gate import ReviewGate
from src.core.evaluate_vacancy_cli import main as evaluate_cli_main

class JobEngineEvidenceTests(unittest.TestCase):
    def test_import_contracts(self):
        self.assertTrue(all([CandidateProfile, ProfileManager, EvidenceRecord, EvidenceRegistry, evaluate_vacancy, ArtifactStore, SimilarityIndex, ReviewGate]))

    def test_profile_validation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            m = ProfileManager(CandidateProfile(candidate_id="c1", candidate_name="Test"), Path(d)/"profile.json")
            self.assertTrue(m.validate()["valid"]); m.save()
            self.assertEqual(ProfileManager.load(Path(d)/"profile.json").profile.candidate_id, "c1")

    def test_unverified_evidence_does_not_support_claim(self):
        r = EvidenceRegistry([EvidenceRecord("e1","Python","SELF_REPORTED","CV",0.7,"2026-11-01",verified_for=["D1"],mapping_reviewed_by="human-reviewer",mapping_reviewed_at="2026-11-01T12:00:00Z")])
        self.assertEqual(r.supports(["e1"], "D1"), [])

    def test_verified_evidence_requires_explicit_requirement_mapping(self):
        evidence = EvidenceRecord("e1","Python automation project","VERIFIED","Project artifact",0.9,"2026-11-01",verified_for=["D1"],mapping_reviewed_by="human-reviewer",mapping_reviewed_at="2026-11-01T12:00:00Z")
        registry = EvidenceRegistry([evidence])
        self.assertEqual(registry.supports(["e1"], "M2"), [])
        self.assertEqual([x.evidence_id for x in registry.supports(["e1"], "D1")], ["e1"])

    def test_mapping_without_human_review_does_not_support_requirement(self):
        evidence = EvidenceRecord("e1","Python","VERIFIED","Project artifact",0.9,"2026-11-01",verified_for=["D1"])
        self.assertEqual(EvidenceRegistry([evidence]).supports(["e1"], "D1"), [])

    def test_missing_evidence_creates_explicit_gap(self):
        v = {"vacancy_id":"v1","requirements":[{"requirement_id":"R1","text":"English C1","type":"mandatory","evidence_refs":[]}]}
        result = evaluate_vacancy(v, {"candidate_id":"c1","evidence_refs":[]}, EvidenceRegistry())
        self.assertEqual(result["requirements"][0]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["critical_gaps"], ["R1"])

    def test_evaluator_uses_private_profile_evidence_not_vacancy_refs(self):
        evidence = EvidenceRecord("e1","Python automation project","VERIFIED","Project artifact",0.9,"2026-11-01",verified_for=["D1"],mapping_reviewed_by="human-reviewer",mapping_reviewed_at="2026-11-01T12:00:00Z")
        registry = EvidenceRegistry([evidence])
        profile = {"candidate_id":"c1","evidence_refs":["e1"]}
        vacancy = {"requirements":[
            {"requirement_id":"M2","text":"Shipped automations","type":"mandatory","evidence_refs":[]},
            {"requirement_id":"D1","text":"Python scripting","type":"desirable","evidence_refs":[]}
        ]}
        result = evaluate_vacancy(vacancy, profile, registry)
        self.assertEqual(result["requirements"][0]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["requirements"][1]["status"], "VERIFIED")
        self.assertEqual(result["requirements"][1]["evidence_ids"], ["e1"])
        self.assertEqual(result["critical_gaps"], ["M2"])
        self.assertEqual(result["recommendation"], "REVIEW")
        self.assertTrue(result["human_review_required"])

    def test_puente_fixture_can_use_private_evidence_without_public_candidate_refs(self):
        fixture_path = Path("tests/fixtures/puente_ai_operations_lead_2660.json")
        vacancy = json.loads(fixture_path.read_text(encoding="utf-8"))
        evidence = EvidenceRecord("e1","Three years of documented operations work","VERIFIED","Employment records",0.95,"2026-11-01",verified_for=["M1"],mapping_reviewed_by="human-reviewer",mapping_reviewed_at="2026-11-01T12:00:00Z")
        result = evaluate_vacancy(vacancy, {"candidate_id":"candidate-local","evidence_refs":["e1"]}, EvidenceRegistry([evidence]))
        self.assertEqual(result["mandatory_total"], 3)
        self.assertEqual(result["mandatory_verified"], 1)
        self.assertEqual(result["requirements"][0]["status"], "VERIFIED")
        self.assertEqual(result["critical_gaps"], ["M2", "M3"])
        self.assertEqual(result["recommendation"], "REVIEW")
        self.assertTrue(result["human_review_required"])

    def test_puente_fixture_evaluates_as_review_with_explicit_gaps(self):
        fixture_path = Path("tests/fixtures/puente_ai_operations_lead_2660.json")
        vacancy = json.loads(fixture_path.read_text(encoding="utf-8"))
        result = evaluate_vacancy(vacancy, {"candidate_id":"candidate-local","evidence_refs":[]}, EvidenceRegistry())
        self.assertEqual(result["recommendation"], "REVIEW")
        self.assertEqual(result["mandatory_total"], 3)
        self.assertEqual(result["mandatory_verified"], 0)
        self.assertEqual(result["critical_gaps"], ["M1", "M2", "M3"])
        self.assertTrue(result["human_review_required"])

    def test_invalid_requirement_type_is_rejected(self):
        v = {"requirements":[{"requirement_id":"R1","text":"X","type":"must-have"}]}
        with self.assertRaises(ValueError):
            evaluate_vacancy(v, {"evidence_refs":[]}, EvidenceRegistry())

    def test_duplicate_requirement_id_is_rejected(self):
        v = {"requirements":[{"requirement_id":"R1","text":"X"},{"requirement_id":"R1","text":"Y"}]}
        with self.assertRaises(ValueError):
            evaluate_vacancy(v, {"evidence_refs":[]}, EvidenceRegistry())

    def test_similarity_is_not_evidence(self):
        idx = SimilarityIndex(Path(tempfile.mkdtemp())/"idx.json")
        idx.register("a","Python automation")
        self.assertTrue(idx.find_exact("Python automation"))
        self.assertFalse(hasattr(idx, "supports"))

    def test_hash_is_reproducible(self):
        payload = {"b":2,"a":1}
        self.assertEqual(ArtifactStore.canonical_hash(payload), ArtifactStore.canonical_hash({"a":1,"b":2}))

    def test_human_review_is_mandatory(self):
        decision = ReviewGate().decide({"recommendation":"APPLY","critical_gaps":[]})
        self.assertEqual(decision.status, "PENDING_HUMAN_REVIEW")
        self.assertTrue(decision.human_review_required)

    def test_cli_creates_review_artifacts_without_submitting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root/"profile.json"
            evidence = root/"evidence.json"
            vacancy = root/"vacancy.json"
            output = root/"reviews"
            profile.write_text(json.dumps({"candidate_id":"c1","candidate_name":"Test","evidence_refs":[]}), encoding="utf-8")
            evidence.write_text(json.dumps({"records":[]}), encoding="utf-8")
            vacancy.write_text(json.dumps({"vacancy_id":"v-cli","source_url":"https://example.invalid/role","requirements":[
                {"requirement_id":"M1","text":"English C1","type":"mandatory","evidence_refs":[]}
            ]}), encoding="utf-8")
            self.assertEqual(evaluate_cli_main(["--profile",str(profile),"--evidence",str(evidence),"--vacancy",str(vacancy),"--output",str(output)]), 0)
            artifact = json.loads((output/"v-cli"/"artifact.json").read_text(encoding="utf-8"))
            self.assertEqual(artifact["payload"]["recommendation"], "REVIEW")
            self.assertEqual(artifact["payload"]["critical_gaps"], ["M1"])
            self.assertTrue(artifact["payload"]["human_review_required"])
            self.assertTrue((output/"v-cli"/"artifact.md").is_file())

    def test_templates_are_valid_json(self):
        for p in ["data/profile/master_profile_template.json","data/profile/evidence_registry_template.json"]:
            json.loads(Path(p).read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
