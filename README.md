# Apply With Proof

Evidence-grounded resume and application tailoring for serious job seekers.

Apply With Proof is a local-first application kit for people whose strongest career evidence is spread across resumes, project notes, case studies, and a free-form career narrative.

The Career Evidence Compiler is the analysis engine behind the product. It does not silently turn narrative material into resume claims. It surfaces candidate evidence, asks the user to approve or reject it, then produces a role-specific application package.

## What is in this first slice

- A structured master profile for approved, reusable claims.
- A free-form career narrative that can reveal overlooked material.
- Job-description fit analysis and evidence matching.
- A review queue with explicit decisions: use for this application, promote to master, context only, or reject.
- Deterministic ATS/parser linting focused on explainable checks rather than a fake universal score.
- Resume, cover-letter, interview-story, application-answer, and review artifacts.
- A browser UI backed by a Python standard-library server. No API key or package install is required.
- An optional prompt-pack output for connecting a local or hosted language model later.
- Public job-page URL extraction with a manual-text fallback for JavaScript-heavy or blocked pages.
- Upload extraction for PDF, DOCX, TXT, Markdown, and RTF resumes or career narratives.

## Start it

From this directory:

```powershell
python app.py
```

Then open <http://127.0.0.1:8765>.

If another local process already uses that port, start it on another one with `$env:CEC_PORT=8766` before running `python app.py`.

The browser stores the working profile, narrative, job description, and review decisions in local browser storage. The server does not persist personal data.

## First-use path

1. Load the example or replace it with a profile containing only claims you are comfortable deploying.
2. Paste a free-form career narrative. This may contain incomplete, tentative, or private material.
3. Paste one target job description.
4. Run analysis.
5. Review every surfaced expansion card.
6. Generate the package only after deciding which candidate evidence is allowed for this application.

You can use a job URL instead of pasting the description. The fetch is best-effort: many job boards render the actual description in JavaScript or block automated requests, so the UI keeps the pasted-text field as the reliable fallback.

An uploaded resume is treated as approved source text for matching and ATS inspection. The structured master profile remains the canonical source used for generated resume structure. An uploaded career narrative is treated like the free-form narrative field and does not become a deployable claim without review.

## Evidence boundary

The system is allowed to discover more than the current resume contains. It is not allowed to silently claim more than the user has reviewed and approved.

Evidence statuses:

- `APPROVED`: reusable in future applications.
- `CANDIDATE`: surfaced from narrative or other source material; not deployable yet.
- `APPLICATION_ONLY`: approved for this role but not promoted globally.
- `CONTEXT_ONLY`: useful for positioning or tone, not a factual claim.
- `NEEDS_VERIFICATION`: potentially useful but incomplete or uncertain.
- `CONTRADICTED`: conflicts with another source.
- `REJECTED`: never use in generated output.

## Repository shape

```text
Apply With Proof/
  app.py                     local HTTP server and JSON API
  engine.py                  deterministic analysis and artifact generation
  data/profile.example.json  generic example, safe to commit
  data/narrative.example.md  generic narrative example
  data/job.example.md        generic job description
  tests/test_engine.py       no-dependency tests for the evidence boundary
  web/                       local UI
```

## Deliberate non-goals for this slice

- No job aggregation or scraping.
- No automatic application submission.
- No credential, OTP, CAPTCHA, or demographic-form handling.
- No claim that an ATS score predicts hiring outcomes.
- No server-side storage of a user's career data.

The next useful increment is a review-first browser side panel for one or two ATS families, not universal autofill.
