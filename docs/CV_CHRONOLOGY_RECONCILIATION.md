# CV Chronology Reconciliation

## Purpose

Import month-level dates and role descriptions from a candidate's source CV into the **private** JOB_ENGINE profile, then connect each employment period to existing claim-level evidence IDs. This is a reconciliation step, not an employment verifier.

## Private profile shape

Store the chronology only in the local, git-ignored candidate profile (for example, `data/private/professional_profile.json`):

```json
{
  "employment_history": [
    {
      "record_id": "CVH-EXAMPLE-001",
      "organization": "Employer name",
      "role_as_stated": "Role copied faithfully from source CV",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM",
      "date_precision": "month",
      "source": "source CV filename and page",
      "verification_status": "SELF_REPORTED",
      "evidence_refs": ["EV-EXAMPLE-001"]
    }
  ]
}
```

An open-ended current activity may use `end_date: null` and a separate source label such as `date_label: "Present (according to source CV)"`. Do not use a fabricated end date.

## Reconciliation procedure

1. Preserve the exact source filename, version, upload date, and page reference in the private record.
2. Transcribe month/year dates and map them to the correct role by inspecting the visual page layout when dates are visually aligned with headings.
3. Keep the source wording separate from normalized role names.
4. Link a period to existing evidence IDs only when the source actually supports the associated claim. Do not link unrelated technical experiments to a commercial employment period.
5. Flag overlaps, unexplained gaps, award-date inconsistencies, and broad activity headings that combine several kinds of work.
6. Split a long-running independent activity into project-level periods before calculating years of experience in a specific technology (especially AI, LLMs, or production automation).
7. Keep all imported records `SELF_REPORTED` until a human reviewer inspects independent corroboration. A CV is documentary evidence of what the candidate declared, not independent proof of employment or deployment.
8. Record evidence-to-vacancy mappings separately, with reviewer identity and timestamp, as required by the Evidence Registry.

## Privacy and safety

- Never commit a real candidate's CV, chronology, dates, employer evidence, personal contact details, or private evidence registry to a public repository.
- Public fixtures must use synthetic organizations and dates and must be explicitly labelled synthetic.
- The import process must not promote evidence status, calculate unqualified years of AI experience, or claim uninterrupted full-time employment.
- The human approval gate for applications remains unchanged.

## Relationship to Evidence Builder

The Evidence Builder creates collection tasks from the private profile's `evidence_refs`. The chronology supplements that registry with time-bounded role context; it does not replace source artifacts such as employment certificates, references, dated project records, execution logs, or attributable deliverables.
