# Busca EMPLEOS — automation starter

First executable foundation for Martín Monzón's job-search workflow.

## What it does
- Imports vacancy records from `data/vacancies.csv` (manual export / authorized source; no scraping or applications are sent).
- Scores evidence-based keyword overlap against `data/profile.json`.
- Produces a triage report and one draft application pack per vacancy under `output/`.
- Marks every candidate `REVIEW_REQUIRED`; there is deliberately no auto-send function.
- Runs tests and a scheduled/manual triage workflow in GitHub Actions.

## Run locally
```bash
python -m src.applybot --profile data/profile.json --vacancies data/vacancies.csv --out output
python -m unittest discover -s tests -v
# Optional Gemini API extraction (requires a Google AI API key):
# python -m src.gemini_extract --notes path/to/notes.txt --out output/gemini_vacancies.json
```

## Input CSV
Required columns: `vacancy_id,company,title,location,work_mode,url,description,requirements,salary,source,posted_date`.
Use a stable `vacancy_id`. Put requirements and description in plain text. Never include private recruiter credentials.

## Profile setup
Edit `data/profile.json` with verified facts only. Keep `evidence` tied to actual CV evidence. Do not add a skill merely because a vacancy asks for it.

## Gemini + NotebookLM workflow (human-controlled)
1. In NotebookLM, use the relevant notebooks as source-grounded research; export/copy only the notes or source extracts you are permitted to use.
2. Ask Gemini to return **only** the JSON structure documented in `docs/GEMINI_VACANCY_CONTRACT.md`, with source URLs and uncertainty noted.
3. Review the output, then import the approved vacancy rows into `data/vacancies.csv`. Do not put Google passwords, cookies, or tokens in the repository.
4. Optional API adapter is included: copy/export the authorized NotebookLM research notes to a local text file, set `GEMINI_API_KEY` in your local environment, then run `python -m src.gemini_extract --notes path/to/notes.txt --out output/gemini_vacancies.json`. The adapter structures only supplied notes; it does not access NotebookLM or browse live vacancies. Review every URL and fact before importing.
5. Inspect generated `output/` artifacts and approve each application yourself.

## GitHub Actions
The workflow runs on a schedule and on manual dispatch. It processes only vacancies already in the repository. The scheduled job does **not** discover live jobs on the internet yet. Outputs are uploaded as workflow artifacts; nothing is sent to employers.

## Safety and limitations
- Match score is a heuristic, not probability of being hired and not a claim of 95% suitability.
- No unsupported claims are added to the profile.
- No email, form, LinkedIn, or job-board submission is automated.
- Store no personal secrets. Review generated files before sharing.
