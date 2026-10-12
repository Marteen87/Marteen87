import csv
import json
import tempfile
import unittest
from pathlib import Path
from src.applybot import score_vacancy, run

class PipelineTests(unittest.TestCase):
    def test_score_uses_only_verified_keywords(self):
        profile = {"verified_keywords": ["ventas", "excel"], "evidence": []}
        vacancy = {"title": "Ejecutivo de ventas", "description": "Ventas B2B", "requirements": "Excel"}
        result = score_vacancy(vacancy, profile)
        self.assertEqual(result["match_score"], 100)
        self.assertEqual(result["approval_status"], "REVIEW_REQUIRED")

    def test_empty_profile_scores_zero(self):
        result = score_vacancy({"title": "Analista", "description": "", "requirements": ""}, {"verified_keywords": []})
        self.assertEqual(result["match_score"], 0)

    def test_pipeline_never_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.json"
            profile.write_text(json.dumps({"candidate_name": "Test", "verified_keywords": ["ventas"], "evidence": []}), encoding="utf-8")
            vacancies = root / "vacancies.csv"
            with vacancies.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["vacancy_id","company","title","location","work_mode","url","description","requirements","salary","source","posted_date"])
                writer.writeheader()
                writer.writerow({"vacancy_id":"v1","company":"Empresa","title":"Ventas","location":"AR","work_mode":"remote","url":"https://example.com/job","description":"ventas","requirements":"ventas","salary":"unknown","source":"test","posted_date":"unknown"})
            out = root / "out"
            payload = run(profile, vacancies, out)
            self.assertEqual(payload["applications_sent"], 0)
            self.assertTrue(payload["human_approval_required"])
            self.assertTrue((out / "applications" / "v1.md").exists())

if __name__ == "__main__":
    unittest.main()
