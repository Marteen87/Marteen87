import unittest

from src.core.evidence_builder import build_collection_plan
from src.core.evidence_registry import EvidenceRecord, EvidenceRegistry


class EvidenceBuilderTests(unittest.TestCase):
    def test_creates_actionable_plan_without_upgrading_self_reported_record(self):
        record = EvidenceRecord(
            "EV-AI-001", "LLM workflow and automation project",
            "SELF_REPORTED", "Candidate statement", 0.5, "2026-11-01"
        )
        plan = build_collection_plan(
            {"candidate_id": "c1", "evidence_refs": ["EV-AI-001"]},
            EvidenceRegistry([record])
        )
        item = plan["evidence_items"][0]
        self.assertEqual(item["current_status"], "SELF_REPORTED")
        self.assertEqual(item["collection_status"], "READY_FOR_HUMAN_COLLECTION")
        self.assertEqual(item["status_change"], "REQUIRES_HUMAN_VERIFICATION")
        self.assertFalse(plan["summary"]["automatic_verification_performed"])
        self.assertIn("workflow diagram", " ".join(item["recommended_artifacts"]).lower())
        self.assertEqual(record.status, "SELF_REPORTED")

    def test_surfaces_missing_registry_reference(self):
        plan = build_collection_plan(
            {"candidate_id": "c1", "evidence_refs": ["EV-MISSING"]},
            EvidenceRegistry()
        )
        self.assertEqual(plan["missing_registry_records"], ["EV-MISSING"])
        self.assertEqual(plan["evidence_items"][0]["current_status"], "MISSING_RECORD")
        self.assertEqual(plan["evidence_items"][0]["status_change"], "PROHIBITED_AUTOMATICALLY")

    def test_verified_record_is_not_reverified_by_builder(self):
        record = EvidenceRecord(
            "EV-COM-001", "B2B commercial pipeline and negotiation",
            "VERIFIED", "Reviewed proposal", 0.9, "2026-11-01",
            verified_for=["REQ-1"], mapping_reviewed_by="reviewer",
            mapping_reviewed_at="2026-11-01T12:00:00Z"
        )
        plan = build_collection_plan(
            {"candidate_id": "c1", "evidence_refs": ["EV-COM-001"]},
            EvidenceRegistry([record])
        )
        item = plan["evidence_items"][0]
        self.assertEqual(item["current_status"], "VERIFIED")
        self.assertEqual(item["collection_status"], "VERIFY_SCOPE_AND_MAPPING")
        self.assertEqual(record.status, "VERIFIED")

    def test_rejects_malformed_profile_references(self):
        with self.assertRaises(ValueError):
            build_collection_plan({"evidence_refs": "EV-1"}, EvidenceRegistry())


if __name__ == "__main__":
    unittest.main()
