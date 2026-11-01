import json, tempfile, unittest
from pathlib import Path
from src.core.profile_manager import CandidateProfile, ProfileManager
from src.core.evidence_registry import EvidenceRecord, EvidenceRegistry
from src.core.compatibility_engine import evaluate_vacancy
from src.core.artifact_store import ArtifactStore
from src.core.similarity_service import SimilarityIndex
from src.core.review_gate import ReviewGate

class JobEngineEvidenceTests(unittest.TestCase):
    def test_import_contracts(self):
        self.assertTrue(all([CandidateProfile, ProfileManager, EvidenceRecord, EvidenceRegistry, evaluate_vacancy, ArtifactStore, SimilarityIndex, ReviewGate]))

    def test_profile_validation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            m = ProfileManager(CandidateProfile(candidate_id="c1", candidate_name="Test"), Path(d)/"profile.json")
            self.assertTrue(m.validate()["valid"]); m.save()
            self.assertEqual(ProfileManager.load(Path(d)/"profile.json").profile.candidate_id, "c1")

    def test_unverified_evidence_does_not_support_claim(self):
        r = EvidenceRegistry([EvidenceRecord("e1","Python","SELF_REPORTED","CV",0.7,"2026-11-01")])
        self.assertEqual(r.supports(["e1"]), [])

    def test_missing_evidence_creates_explicit_gap(self):
        v = {"vacancy_id":"v1","requirements":[{"requirement_id":"R1","text":"English C1","type":"mandatory","evidence_refs":[]}]}
        result = evaluate_vacancy(v, {"candidate_id":"c1","evidence_refs":[]}, EvidenceRegistry())
        self.assertEqual(result["requirements"][0]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["critical_gaps"], ["R1"])

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

    def test_templates_are_valid_json(self):
        for p in ["data/profile/master_profile_template.json","data/profile/evidence_registry_template.json"]:
            json.loads(Path(p).read_text(encoding="utf-8"))

if __name__ == "__main__": unittest.main()
