import json
import tempfile
import unittest
from pathlib import Path

from src.core.application_workflow import (
    ApplicationWorkflowError,
    prepare_application,
    record_confirmed_submission,
    record_human_decision,
)
from src.core.evidence_registry import EvidenceRegistry

class AssistedApplicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.vacancy = {
            "vacancy_id": "vacancy-001",
            "title": "Asesor Comercial B2B",
            "company": "Empresa Ejemplo",
            "source_url": "https://careers.example.org/jobs/001",
            "verification_status": "VERIFIED",
            "source_verified_by": "human-reviewer",
            "source_verified_at": "2026-11-02T10:00:00Z",
            "requirements": [
                {"requirement_id": "M1", "text": "B2B sales experience", "type": "mandatory"},
                {"requirement_id": "D1", "text": "CRM experience", "type": "desirable"},
            ],
        }
        self.profile = {
            "candidate_id": "candidate-local",
            "candidate_name": "Candidate Example",
            "headline": "Senior commercial advisor",
            "skills": ["B2B sales", "negotiation"],
            "evidence_refs": [],
        }

    def test_prepare_creates_pack_but_does_not_submit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = prepare_application(self.vacancy, self.profile, EvidenceRegistry(), tmp)
            folder = Path(tmp) / "vacancy-001"
            self.assertEqual(result["status"], "PREPARED_PENDING_HUMAN_APPROVAL")
            self.assertTrue((folder / "application.json").is_file())
            self.assertTrue((folder / "application.md").is_file())
            self.assertTrue((folder / "tailored_cv.md").is_file())
            self.assertTrue((folder / "cover_letter.md").is_file())
            cv_text = (folder / "tailored_cv.md").read_text(encoding="utf-8")
            letter_text = (folder / "cover_letter.md").read_text(encoding="utf-8")
            self.assertIn("Senior commercial advisor", cv_text)
            self.assertIn("Candidate Example", letter_text)
            self.assertIn("pending human review", letter_text.lower())
            self.assertIsNone(result["human_decision"])
            self.assertIsNone(result["submission"])
            self.assertEqual(result["evaluation"]["mandatory_verified"], 0)

    def test_blocks_unverified_vacancy(self):
        bad = dict(self.vacancy, verification_status="UNVERIFIED")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApplicationWorkflowError):
                prepare_application(bad, self.profile, EvidenceRegistry(), tmp)

    def test_blocks_missing_source_review_metadata(self):
        bad = dict(self.vacancy, source_verified_by="", source_verified_at="")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApplicationWorkflowError):
                prepare_application(bad, self.profile, EvidenceRegistry(), tmp)

    def test_rejects_path_traversal_vacancy_id(self):
        bad = dict(self.vacancy, vacancy_id="../outside")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApplicationWorkflowError):
                prepare_application(bad, self.profile, EvidenceRegistry(), tmp)

    def test_approval_requires_explicit_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare_application(self.vacancy, self.profile, EvidenceRegistry(), tmp)
            path = Path(tmp) / "vacancy-001" / "application.json"
            with self.assertRaises(ApplicationWorkflowError):
                record_human_decision(path, decision="APPROVE", reviewer="")

    def test_rejection_is_terminal_for_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare_application(self.vacancy, self.profile, EvidenceRegistry(), tmp)
            path = Path(tmp) / "vacancy-001" / "application.json"
            rejected = record_human_decision(path, decision="REJECT", reviewer="candidate")
            self.assertEqual(rejected["status"], "REJECTED_BY_HUMAN")
            with self.assertRaises(ApplicationWorkflowError):
                record_confirmed_submission(path, channel="portal", confirmation_reference="receipt", reviewer="candidate")


    def test_tampered_pack_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare_application(self.vacancy, self.profile, EvidenceRegistry(), tmp)
            path = Path(tmp) / "vacancy-001" / "application.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["candidate_snapshot"]["headline"] = "Tampered claim"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ApplicationWorkflowError):
                record_human_decision(path, decision="APPROVE", reviewer="candidate")

    def test_submission_requires_prior_approval_and_external_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare_application(self.vacancy, self.profile, EvidenceRegistry(), tmp)
            path = Path(tmp) / "vacancy-001" / "application.json"
            with self.assertRaises(ApplicationWorkflowError):
                record_confirmed_submission(path, channel="portal", confirmation_reference="receipt", reviewer="candidate")
            record_human_decision(path, decision="APPROVE", reviewer="candidate")
            with self.assertRaises(ApplicationWorkflowError):
                record_confirmed_submission(path, channel="portal", confirmation_reference="", reviewer="candidate")
            submitted = record_confirmed_submission(
                path, channel="portal", confirmation_reference="external-receipt-123", reviewer="candidate"
            )
            self.assertEqual(submitted["status"], "SUBMITTED_CONFIRMED")

if __name__ == "__main__":
    unittest.main()
