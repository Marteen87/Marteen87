# Assisted application workflow

## Purpose

Prepare a vacancy-specific, evidence-traceable application pack and enforce an explicit human approval decision before submission. This module does not send email or submit external forms.

## Run

    from pathlib import Path
    import json
    from src.core.application_workflow import prepare_application
    from src.core.evidence_registry import EvidenceRegistry

    vacancy = json.loads(Path("path/to/verified_vacancy.json").read_text(encoding="utf-8"))
    profile = json.loads(Path("data/private/professional_profile.json").read_text(encoding="utf-8"))
    registry = EvidenceRegistry.from_file("data/private/evidence_registry.json")
    pack = prepare_application(vacancy, profile, registry, "data/applications/prepared")

A vacancy is eligible only when it contains:
- verification_status: VERIFIED
- a real HTTPS source_url
- source_verified_by and source_verified_at
- a structured, non-empty requirements array

## State machine

- PREPARED_PENDING_HUMAN_APPROVAL: pack generated; no external action.
- APPROVED_READY_TO_SUBMIT: an identified human explicitly approved it.
- REJECTED_BY_HUMAN: human rejected it; submission is blocked.
- SUBMITTED_CONFIRMED: an external submission has already happened and a receipt/reference was recorded. The function only records confirmation; it does not submit.

## Evidence and privacy

- The candidate snapshot copies only fields present in the private profile. It does not invent missing experience, tools, metrics, or qualifications.
- Requirement coverage comes from the evidence-first compatibility engine and its explicit evidence mapping rules.
- Candidate profiles and application packs belong in local private storage; never commit them to this public repository.
- A prepared pack is not an approved application, and an approval is not proof of submission.
