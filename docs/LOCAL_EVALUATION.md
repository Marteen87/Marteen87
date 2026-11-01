# Local vacancy evaluation

The evaluation engine is local-first. Keep the real candidate profile and evidence registry under `data/private/`; that directory is excluded from Git by the repository's `.gitignore`.

## Required local files

- `data/private/professional_profile.json`
- `data/private/evidence_registry.json`

Start from the private starter package prepared separately for the candidate. Do not commit those files to a public repository.

## Run

From the repository root:

```bash
python -m src.core.evaluate_vacancy_cli
```

The default command evaluates `tests/fixtures/puente_ai_operations_lead_2660.json`. To evaluate another structured vacancy:

```bash
python -m src.core.evaluate_vacancy_cli --vacancy path/to/vacancy.json
```

Optional arguments:

- `--profile`: candidate profile JSON path
- `--evidence`: evidence registry JSON path
- `--output`: output directory (default: `data/applications/reviews`)

The command writes JSON and Markdown review artifacts, including a SHA-256 hash and provenance. It does not send applications, create emails, or submit forms.

## Evidence policy

A record must be `VERIFIED`, be referenced by the profile and requirement, and include an explicit requirement mapping with reviewer identity and timestamp before it can support that requirement. Similarity scores are not evidence. Every result remains `REVIEW`; human approval is always required.
