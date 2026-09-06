"""Offline, explainable analysis for the Career Evidence Compiler MVP.

This module intentionally avoids an LLM. It establishes the evidence boundary,
review decisions, and artifact contract before adding model-generated prose.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "been", "being", "but",
    "can", "company", "for", "from", "have", "into", "its", "more", "our", "role",
    "that", "their", "they", "this", "through", "with", "will", "you", "your",
    "the", "who", "what", "when", "where", "which", "while", "years", "year",
}

DOMAIN_TERMS = [
    "product marketing", "product management", "go-to-market", "go to market",
    "business development", "business systems", "cross-functional", "stakeholder",
    "customer discovery", "market research", "competitive analysis", "channel strategy",
    "partner strategy", "revenue operations", "crm", "automation", "workflow",
    "analytics", "data", "ai", "machine learning", "python", "sql", "n8n", "zoho",
    "zapier", "content strategy", "positioning", "messaging", "launch", "roadmap",
    "portfolio", "sales enablement", "operations", "strategy", "leadership", "growth",
]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9+.#/-]{2,}", (text or "").lower())


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _profile_text(profile: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("name", "headline", "summary"):
        value = profile.get(key, "")
        if isinstance(value, str):
            chunks.append(value)
    skills = profile.get("skills", [])
    if isinstance(skills, list):
        chunks.extend(str(item) for item in skills)
    for experience in profile.get("experiences", []) or []:
        if not isinstance(experience, dict):
            continue
        chunks.extend(str(experience.get(key, "")) for key in ("company", "title", "dates"))
        bullets = experience.get("bullets", [])
        if isinstance(bullets, list):
            chunks.extend(str(item) for item in bullets)
    return " ".join(chunks)


def _job_terms(job_description: str) -> list[str]:
    job = _normal(job_description)
    explicit = [term for term in DOMAIN_TERMS if term in job]
    counts = Counter(word for word in _words(job) if word not in STOPWORDS)
    common = [word for word, count in counts.most_common(20) if count >= 1]
    terms: list[str] = []
    for term in explicit + common:
        if term not in terms and len(term) > 2:
            terms.append(term)
    return terms[:28]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text or "") if part.strip()]


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    lowered = _normal(text)
    return [term for term in terms if term in lowered]


def _candidate_cards(narrative: str, terms: list[str]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for index, sentence in enumerate(_sentences(narrative), start=1):
        matches = _matched_terms(sentence, terms)
        has_signal = bool(re.search(r"\b(led|built|created|launched|grew|reduced|increased|improved|designed|managed|developed|consolidated|owned|drove)\b", sentence, re.I))
        if matches and has_signal:
            cards.append({
                "id": f"narrative-{index}",
                "claim": sentence,
                "source": f"career narrative, paragraph {index}",
                "matched_terms": matches,
                "status": "CANDIDATE",
                "confidence": "medium",
                "review_questions": [
                    "Is this factually accurate as written?",
                    "What scale, timeframe, or outcome can be safely added?",
                    "Should this be reusable globally or only for this application?",
                ],
            })
    return cards[:12]


def _approved_matches(profile: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for experience in profile.get("experiences", []) or []:
        if not isinstance(experience, dict):
            continue
        for bullet in experience.get("bullets", []) or []:
            matched = _matched_terms(str(bullet), terms)
            if matched:
                matches.append({
                    "claim": str(bullet),
                    "source": f"approved profile: {experience.get('company', 'experience')}",
                    "matched_terms": matched,
                    "status": "APPROVED",
                })
    return matches[:20]


def _approved_resume_matches(resume_text: str, terms: list[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line in _sentences(resume_text):
        matched = _matched_terms(line, terms)
        if matched:
            matches.append({
                "claim": line,
                "source": "uploaded master resume",
                "matched_terms": matched,
                "status": "APPROVED",
            })
    return matches[:20]


def _ats_report(resume_text: str, profile: dict[str, Any]) -> dict[str, Any]:
    text = resume_text or _profile_text(profile)
    lowered = text.lower()
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(label: str, passed: bool, detail: str) -> None:
        checks.append({"label": label, "passed": passed, "detail": detail})

    check("Plain text is present", bool(text.strip()), "The parser has text to inspect.")
    check("Standard section vocabulary", any(term in lowered for term in ("experience", "work history", "education", "skills")), "Use conventional section headings where they fit.")
    check("No obvious table/column markers", not ("|" in text or "\t" in text), "Tables and columns can be difficult for some parsers.")
    check("Contact information is in body text", bool(re.search(r"@|\+?\d[\d ()-]{7,}", text)), "Do not rely only on header/footer content for contact details.")
    check("Dates are visible", bool(re.search(r"\b20\d{2}\b", text)), "Make employment dates explicit and consistent.")
    if "|" in text or "\t" in text:
        warnings.append("Table or tabular layout markers detected; prefer a single-column export.")
    if not any(term in lowered for term in ("experience", "work history", "education", "skills")):
        warnings.append("No conventional section heading was detected.")
    if not text.strip():
        warnings.append("No resume text was provided; run the report again with a master profile or resume text.")
    passed = sum(1 for item in checks if item["passed"])
    return {
        "label": "Good" if passed >= 4 else "Needs review",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "warnings": warnings,
        "disclaimer": "This is a transparent parser-readiness report, not a prediction of hiring outcomes or a universal ATS score.",
    }


def analyze_application(profile: dict[str, Any], narrative: str, job_description: str, resume_text: str = "") -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("profile must be a JSON object")
    if not (job_description or "").strip():
        raise ValueError("job_description is required")
    terms = _job_terms(job_description)
    profile_text = _profile_text(profile)
    approved = _approved_matches(profile, terms) + _approved_resume_matches(resume_text, terms)
    narrative_cards = _candidate_cards(narrative, terms)
    represented = {term for item in approved for term in item["matched_terms"]}
    missing = [term for term in terms if term not in represented]
    coverage = round(len(represented) / max(len(terms), 1), 2)
    if coverage >= 0.65:
        recommendation = "Strong apply"
    elif coverage >= 0.4:
        recommendation = "Apply after evidence review"
    else:
        recommendation = "Stretch apply / gather more proof"
    return {
        "job_terms": terms,
        "approved_matches": approved[:30],
        "candidate_evidence": narrative_cards,
        "missing_terms": missing,
        "coverage": coverage,
        "recommendation": recommendation,
        "fit_note": "Coverage is a review aid, not a hiring probability. Read the evidence and gaps before deciding.",
        "ats_report": _ats_report(resume_text or profile_text, profile),
        "profile_text_present": bool(profile_text.strip()),
    }


def _allowed_candidate_cards(analysis: dict[str, Any], decisions: dict[str, str]) -> list[dict[str, Any]]:
    allowed: list[dict[str, Any]] = []
    for card in analysis.get("candidate_evidence", []) or []:
        decision = decisions.get(card["id"], "pending")
        if decision in {"application_only", "promote"}:
            allowed.append({**card, "decision": decision})
    return allowed


def _resume_markdown(profile: dict[str, Any], approved: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> str:
    lines = [f"# {profile.get('name', 'Your Name')}"]
    contact = profile.get("contact", {}) or {}
    contact_line = " · ".join(str(contact.get(key)) for key in ("email", "phone", "location", "linkedin") if contact.get(key))
    if contact_line:
        lines.append(contact_line)
    if profile.get("headline"):
        lines.extend(["", f"## {profile['headline']}"])
    if profile.get("summary"):
        lines.extend(["", profile["summary"]])
    lines.extend(["", "## Experience"])
    for exp in profile.get("experiences", []) or []:
        lines.extend(["", f"### {exp.get('title', 'Role')} — {exp.get('company', 'Company')}", str(exp.get("dates", ""))])
        for bullet in exp.get("bullets", []) or []:
            lines.append(f"- {bullet}")
    if candidate:
        lines.extend(["", "## Relevant evidence approved for this application"])
        for item in candidate:
            lines.append(f"- {item['claim']}")
    if profile.get("skills"):
        lines.extend(["", "## Skills", ", ".join(str(skill) for skill in profile["skills"])])
    return "\n".join(lines).strip() + "\n"


def _cover_letter(profile: dict[str, Any], job_description: str, approved: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> str:
    company_match = re.search(r"\b(?:at|with|join)\s+([A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+){0,3})", job_description)
    company = company_match.group(1).strip() if company_match else "your team"
    name = profile.get("name", "Your Name")
    evidence = approved[:2] + candidate[:2]
    proof = " ".join(item["claim"] for item in evidence) or profile.get("summary", "")
    return (f"Dear Hiring Team at {company},\n\n"
            f"I am interested in the opportunity because it calls for someone who can connect strategy, execution, and measurable operating progress. "
            f"My background is centered on turning ambiguous commercial and operational problems into systems that teams can use.\n\n"
            f"Relevant evidence includes: {proof}\n\n"
            f"I would welcome the opportunity to discuss how that combination of judgment and execution could help {company}.\n\n"
            f"Best,\n{name}\n")


def generate_package(profile: dict[str, Any], narrative: str, job_description: str, analysis: dict[str, Any], decisions: dict[str, str]) -> dict[str, Any]:
    if not analysis:
        analysis = analyze_application(profile, narrative, job_description)
    candidate = _allowed_candidate_cards(analysis, decisions or {})
    approved = analysis.get("approved_matches", [])
    resume = _resume_markdown(profile, approved, candidate)
    letter = _cover_letter(profile, job_description, approved, candidate)
    stories = "\n".join(f"- {item['claim']}\n  Source: {item['source']}" for item in approved[:6] + candidate[:6])
    answers = "\n".join([
        "# Application answers",
        "",
        "## Why are you interested in this role?",
        "Use the approved role motivation and evidence above; revise in your own voice before submitting.",
        "",
        "## What experience is most relevant?",
        stories or "No approved evidence yet. Review the evidence queue before drafting an answer.",
    ])
    prompt_pack = f"""You are helping tailor a truthful application package.

Use only APPROVED PROFILE CLAIMS and APPLICATION-APPROVED EVIDENCE. Do not invent employers, dates, metrics, titles, technologies, or outcomes. If evidence is incomplete, mark it as a question.

JOB DESCRIPTION:
{job_description}

APPROVED PROFILE:
{_profile_text(profile)}

APPROVED EXPANSIONS FOR THIS APPLICATION:
{stories or '(none)'}

Produce a concise resume, a specific cover letter, and five interview stories. Explain any unresolved evidence gaps.
"""
    return {
        "resume": resume,
        "cover_letter": letter,
        "interview_stories": stories or "No approved evidence yet.",
        "application_answers": answers,
        "ats_report": analysis.get("ats_report", {}),
        "review_ledger": [
            {"id": card["id"], "claim": card["claim"], "decision": decisions.get(card["id"], "pending"), "source": card["source"]}
            for card in analysis.get("candidate_evidence", []) or []
        ],
        "prompt_pack": prompt_pack,
    }
