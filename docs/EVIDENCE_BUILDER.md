# Evidence Builder

## Purpose

Turn each private-profile evidence reference into a concrete collection and review task. The builder is a planning aid, not an evidence verifier, CV writer, or application sender.

## Run locally

From the repository root, with the candidate's private profile and registry stored outside Git (for example under `data/private/`):

```python
from pathlib import Path
import json
from src.core.evidence_registry import EvidenceRegistry
from src.core.evidence_builder import build_collection_plan

profile = json.loads(Path("data/private/professional_profile.json").read_text(encoding="utf-8"))
registry = EvidenceRegistry.from_file("data/private/evidence_registry.json")
plan = build_collection_plan(profile, registry)
Path("data/private/evidence_collection_plan.json").write_text(
    json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

The output is a private working artifact. Do not commit it to a public repository.

## Workflow

1. Open each evidence item and collect the recommended original artifacts.
2. Redact secrets, personal data, and confidential third-party information before storing or sharing copies.
3. Record source, date, provenance, and the exact part of the claim supported.
4. Have a human reviewer assess authenticity and candidate attribution.
5. Separately map the evidence to a vacancy requirement. Record reviewer identity and timestamp in the private evidence registry.
6. Only then may a record be marked `VERIFIED`; the existing evaluator additionally requires the explicit requirement mapping and its human review metadata.

## Status rules

- `SELF_REPORTED`: claim recorded, but source evidence has not passed review.
- `PARTIAL`: some supporting material exists, but scope or claim is incomplete.
- `UNKNOWN`: not enough information to assess.
- `SYNTHETIC`: generated test material; never professional experience.
- `VERIFIED`: only after a human checks authentic source material. This builder never assigns this status.

A missing registry record is surfaced as `MISSING_RECORD`; the builder does not silently create or repair evidence.

## Security

Candidate profiles, evidence files, contact information, employment documents, and generated collection plans belong in the ignored private data directory. Use sanitized examples only in tests and public fixtures.
