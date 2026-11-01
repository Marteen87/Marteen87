import json
import unittest
from pathlib import Path

from src.core.compatibility_engine import evaluate_vacancy
from src.core.evidence_registry import EvidenceRegistry
from src.core.review_gate import ReviewGate


class RehireBusinessDevelopmentFixtureTests(unittest.TestCase):
    def test_rehire_automotive_b2b_fixture_requires_human_review(self):
        fixture = Path("tests/fixtures/rehire_business_development_automotive_2026_10_30.json")
        vacancy = json.loads(fixture.read_text(encoding="utf-8"))
        result = evaluate_vacancy(
            vacancy,
            {"candidate_id": "candidate-local", "evidence_refs": []},
            EvidenceRegistry(),
        )
        self.assertEqual(result["recommendation"], "REVIEW")
        self.assertEqual(result["mandatory_total"], 10)
        self.assertEqual(result["mandatory_verified"], 0)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["critical_gaps"], [f"M{i}" for i in range(1, 11)])
        decision = ReviewGate().decide(result)
        self.assertEqual(decision.status, "PENDING_HUMAN_REVIEW")
        self.assertTrue(decision.human_review_required)


if __name__ == "__main__":
    unittest.main()
