from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.applybot import read_vacancies, run, score_vacancy, vacancy_is_verified
from src.gmail_draft import build_email_message


class PipelineTests(unittest.TestCase):
    def test_exact_keyword_matches_are_transparent(self):
        vacancy = {"title": "Ejecutivo de ventas", "description": "Negociación B2B", "requirements": "Excel"}
        profile = {"verified_keywords": ["ventas", "negociación", "B2B", "Excel", "SAP"]}
        result = score_vacancy(vacancy, profile)
        self.assertEqual(result["match_score"], 80)
        self.assertEqual(result["matched_verified_keywords"], ["B2B", "Excel", "negociación", "ventas"])
        self.assertEqual(result["other_profile_keywords_not_found"], ["SAP"])

    def test_empty_profile_scores_zero_without_inventing_skills(self):
        result = score_vacancy({"title": "Ejecutivo", "description": "ventas", "requirements": "B2B"}, {})
        self.assertEqual(result["match_score"], 0)
        self.assertEqual(result["matched_verified_keywords"], [])

    def test_duplicate_vacancy_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vacancies.csv"
            headers = ["vacancy_id","company","title","location","work_mode","url","description","requirements","salary","source","posted_date"]
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                row = dict(zip(headers, ["v1","A","B","AR","remote","https://a.com","d","r","?","manual","2026-01-01"]))
                writer.writerow(row)
                writer.writerow(row)
            with self.assertRaises(ValueError):
                read_vacancies(path)

    def test_unverified_or_example_vacancy_is_blocked_from_gmail(self):
        self.assertFalse(vacancy_is_verified({"url":"https://example.com/job","verification_status":"VERIFIED"}))
        self.assertFalse(vacancy_is_verified({"url":"https://company.com/job"}))
        self.assertTrue(vacancy_is_verified({"url":"https://company.com/jobs/1","verification_status":"VERIFIED"}))

    def test_gmail_draft_requires_explicit_valid_recipient(self):
        vacancy = {"company":"Empresa","title":"Ejecutivo"}
        with self.assertRaises(ValueError):
            build_email_message(vacancy, {"candidate_name":"Candidato"}, ["ventas"])
        msg = build_email_message(vacancy, {"candidate_name":"Candidato"}, ["ventas"], to_address="talento@empresa.com")
        self.assertEqual(msg["to"], "talento@empresa.com")
        self.assertIn("borrador pendiente", msg["body"])

    def test_pipeline_never_sends_and_unverified_vacancy_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            profile = base / "profile.json"
            profile.write_text(json.dumps({"candidate_name":"Candidato","verified_keywords":[],"evidence":[]}), encoding="utf-8")
            vacancies = base / "vacancies.csv"
            headers = ["vacancy_id","company","title","location","work_mode","url","description","requirements","salary","source","posted_date"]
            with vacancies.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerow(dict(zip(headers, ["v1","Empresa","Ejecutivo","AR","remote","https://example.com/v1","ventas","ventas","?","manual-test","2026-11-01"])))
            payload = run(profile, vacancies, base / "out", gmail_draft=True, gmail_to="talento@empresa.com")
            self.assertEqual(payload["applications_sent"], 0)
            self.assertTrue(payload["human_approval_required"])
            self.assertEqual(payload["results"][0]["gmail_draft_status"], "BLOCKED_UNVERIFIED_VACANCY")


if __name__ == "__main__":
    unittest.main()
