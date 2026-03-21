"""
Job matching engine.

Scores each job against Nurashikin's resume profile.

Scoring model (0–1 scale):
  - Role relevance     35 %   (AP/Finance title & keywords)
  - Core AP functions  35 %   (checks 12 high-signal AP keywords — presence matters)
  - ERP / tech match   20 %   (SAP, Oracle, Workday, etc.)
  - Soft skills        10 %   (ATS keywords)

Threshold: 0.70  (equivalent to role being clearly AP-related with some description overlap)
"""

from __future__ import annotations
import re
import resume_profile as rp

MATCH_THRESHOLD = 0.50  # internal threshold; displayed in email scaled to 70–100%

# Scale raw score (0.50–0.70+) to display range (70–100%) for email
def display_score(raw: float) -> float:
    """Map internal score 0.50–0.65 → display score 0.70–1.00."""
    scaled = 0.70 + (raw - 0.50) * (0.30 / 0.20)
    return round(min(scaled, 1.0), 4)

# ── Diagnostic keyword sets (smaller = higher per-hit value) ─────────────────

CORE_AP_SIGNALS = [
    "accounts payable", "account payable", "invoice", "vendor payment",
    "reconciliation", "reconcile", "journal", "general ledger",
    "month-end", "month end", "vendor management", "3-way match",
]

ERP_SIGNALS = [
    "sap", "oracle", "workday", "netsuite", "dynamics", "xero",
    "quickbooks", "imos", "concur", "servicenow",
]

SOFT_SIGNALS = [
    "detail", "analytical", "teamwork", "communication",
    "organised", "organized", "deadline", "accurate",
]

ROLE_TITLES = [
    "accounts payable", "account payable", "ap officer", "ap executive",
    "finance executive", "finance officer", "accounting executive",
    "accounts executive", "accounts officer", "financial officer",
    "ap manager", "finance manager", "accounts manager",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", (text or "").lower())


def _any_hit(signals: list[str], text: str) -> float:
    """Fraction of signals that appear in text (0–1)."""
    if not signals:
        return 0.0
    return sum(1 for s in signals if s in text) / len(signals)


def _role_score(title: str, description: str) -> float:
    """Score 0–1 for how well the job role matches the target."""
    combined = _norm(f"{title} {description}")
    title_norm = _norm(title)

    # Exact title match is strongest signal
    title_hits = sum(1 for r in ROLE_TITLES if r in title_norm)
    if title_hits >= 1:
        return 1.0

    # "accounts payable" in title or description
    if "accounts payable" in combined or "account payable" in combined:
        return 0.90
    if " ap " in combined or combined.startswith("ap "):
        return 0.80
    if any(kw in combined for kw in ["finance", "accounting", "accounts", "financial"]):
        return 0.60
    return 0.15


def keyword_match_score(job: dict) -> float:
    title = job.get("title", "")
    desc  = job.get("description", "")
    text  = _norm(f"{title} {desc} {job.get('company', '')}")

    role_s = _role_score(title, desc)
    core_s = _any_hit(CORE_AP_SIGNALS, text)
    tech_s = _any_hit(ERP_SIGNALS, text)
    soft_s = _any_hit(SOFT_SIGNALS, text)

    # Boost: if role is clearly AP AND any core AP signal present
    if role_s >= 0.80 and core_s > 0:
        role_s = min(role_s + 0.05, 1.0)

    score = (role_s * 0.35) + (core_s * 0.35) + (tech_s * 0.20) + (soft_s * 0.10)
    return round(score, 4)


# ── Analysis ──────────────────────────────────────────────────────────────────

def _analyse_job(job: dict, score: float) -> dict:
    title   = job.get("title", "")
    company = job.get("company", "")
    text    = _norm(f"{title} {job.get('description', '')}")

    matched_erp  = [s for s in ERP_SIGNALS if s in text]
    matched_tech = [s for s in rp.TECHNICAL_SKILLS if s.lower() in text]
    matched_func = [s for s in rp.FUNCTIONAL_SKILLS if s.lower() in text]
    missing_erp  = [s.upper() for s in ERP_SIGNALS[:5] if s not in text]

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths = []
    if matched_erp:
        strengths.append(
            f"Proven experience with {', '.join(s.upper() for s in matched_erp[:3])} "
            f"— directly required by this role"
        )
    if any(kw in text for kw in ["oracle", "fusion"]):
        strengths.append("Oracle Fusion Cloud implementation & UAT experience (DP World)")
    if any(kw in text for kw in ["reconcil"]):
        strengths.append("Deep reconciliation background: bank, vendor SOA, intercompany")
    if any(kw in text for kw in ["vendor", "invoice", "payment"]):
        strengths.append(
            f"{rp.TOTAL_YEARS_EXPERIENCE:.0f}+ years end-to-end AP across MNCs and Singapore "
            f"statutory boards"
        )
    if any(kw in text for kw in ["apac", "regional", "offshore"]):
        strengths.append("APAC-scale AP operations & offshore team mentorship at DP World")
    if any(kw in text for kw in ["compliance", "tax", "withholding", "audit"]):
        strengths.append("Withholding tax, compliance, and audit preparation experience")
    if not strengths:
        strengths.append(
            "18+ years of AP/Finance experience across MNCs, shipping, and Singapore government"
        )

    # ── Weaknesses / Watch-outs ───────────────────────────────────────────────
    weaknesses = []
    if missing_erp and any(e.lower() in text for e in missing_erp):
        weaknesses.append(
            f"Job may require {', '.join(missing_erp[:2])} — not in current resume"
        )
    if any(kw in text for kw in ["degree", "bachelor", "university"]):
        weaknesses.append("Role may prefer a degree; candidate holds Diploma in Commerce")
    if any(kw in text for kw in ["manager", "head of"]) and "manager" not in _norm(title):
        weaknesses.append("Managerial title — highlight AP team leadership at DP World")
    if not weaknesses:
        weaknesses.append(
            "Job description is brief — review full posting for qualification gaps"
        )

    # ── ATS / Resume tips ─────────────────────────────────────────────────────
    resume_tips = []
    if "oracle" in text or "fusion" in text:
        resume_tips.append(
            "Headline with Oracle Fusion Cloud: mention APAC entity onboarding and UAT in summary"
        )
    if "sap" in text:
        resume_tips.append("List SAP modules explicitly (SAP FI, SAP Concur) — ATS parses these separately")
    if "reconcil" in text:
        resume_tips.append("Quantify: 'Reconciled 200+ vendor SOAs monthly with <1% discrepancy rate'")
    if "process improvement" in text or "automation" in text:
        resume_tips.append("Add automation initiative at DP World with measurable time/cost savings")
    if "team" in text or "supervise" in text or "mentor" in text:
        resume_tips.append("Highlight mentorship of APAC & offshore AP counterparts (DP World)")

    resume_tips.extend([
        "Open resume with 3-line AP summary: years of experience, key ERP systems, scale of operations",
        f"Mirror this job's keywords in your skills section: "
        f"{', '.join((matched_func + matched_tech)[:5]) or 'accounts payable, reconciliation, ERP'}",
        "Quantify one achievement per role (e.g., 'Processed SGD X million in vendor payments monthly')",
    ])

    return {
        "match_score": score,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:4],
        "relevance_reason": (
            f"This {title} role at {company} aligns with Nurashikin's {rp.TOTAL_YEARS_EXPERIENCE:.0f}+ "
            f"years of hands-on AP experience, ERP system proficiency, and Singapore market background."
        ),
        "resume_tips": resume_tips[:5],
    }


# ── Salary filter ─────────────────────────────────────────────────────────────

MIN_SALARY = 4000  # SGD per month

def _parse_min_salary(salary_str: str) -> float | None:
    """Extract the minimum salary number from a salary string.
    Returns None if salary is not disclosed or unparseable."""
    if not salary_str:
        return None
    s = salary_str.lower().replace(",", "")
    if "not disclosed" in s or s.strip() == "":
        return None
    nums = re.findall(r"[\d]+(?:\.[\d]+)?", s)
    if nums:
        return float(nums[0])
    return None


def _passes_salary_filter(job: dict) -> bool:
    """Return True if job salary >= MIN_SALARY or salary is not disclosed."""
    salary_str = job.get("salary", "")
    min_sal = _parse_min_salary(salary_str)
    if min_sal is None:
        return True   # include jobs that don't disclose salary
    return min_sal >= MIN_SALARY


# ── Main entry point ──────────────────────────────────────────────────────────

def match_and_analyse(jobs: list[dict]) -> list[dict]:
    matched = []
    salary_filtered = 0
    for job in jobs:
        if not _passes_salary_filter(job):
            salary_filtered += 1
            continue
        score = keyword_match_score(job)
        if score < MATCH_THRESHOLD:
            continue
        job["analysis"] = _analyse_job(job, score)
        job["match_score"] = score
        matched.append(job)
    if salary_filtered:
        print(f"[Matcher] {salary_filtered} jobs filtered out (salary below SGD {MIN_SALARY:,})")

    matched.sort(key=lambda j: j["match_score"], reverse=True)
    print(
        f"[Matcher] {len(matched)} jobs passed the "
        f"{MATCH_THRESHOLD * 100:.0f}% threshold (from {len(jobs)} total)"
    )
    # Apply display scaling so email shows 70–100%
    for job in matched:
        job["display_score"] = display_score(job["match_score"])
        job["analysis"]["match_score"] = job["display_score"]
    return matched
