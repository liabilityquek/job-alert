"""
Underwriting assistant job matching engine.

Scores each job against Nurashikin's transferable skills for underwriting roles.

Scoring model (0–1 scale):
  - Role relevance        30 %   (underwriting / insurance title & keywords)
  - Transferable skills   35 %   (AP/finance skills that transfer to underwriting)
  - Technical match       20 %   (data analysis, Excel, systems)
  - Soft skills           15 %   (detail-oriented, communication, analytical)

Threshold: 0.40  (lower bar — maps to ≥50% display score)
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta
import resume_profile as rp

MATCH_THRESHOLD = 0.40

# Scale raw score to display range (50–100%) for email
def display_score(raw: float) -> float:
    """Map internal score 0.40–0.65 → display score 0.50–1.00."""
    scaled = 0.50 + (raw - 0.40) * (0.50 / 0.25)
    return round(min(max(scaled, 0.50), 1.0), 4)


# ── Keyword sets ──────────────────────────────────────────────────────────────

UNDERWRITING_ROLE_TITLES = [
    "underwriting assistant", "underwriting executive", "underwriting officer",
    "underwriting analyst", "underwriter", "insurance assistant",
    "insurance executive", "insurance officer", "insurance analyst",
    "claims assistant", "claims executive", "claims officer",
    "reinsurance", "policy admin", "policy administrator",
]

UNDERWRITING_SIGNALS = [
    "underwriting", "insurance", "policy", "premium", "risk assessment",
    "claims", "reinsurance", "broker", "insurer", "coverage",
    "endorsement", "renewal", "treaty", "facultative", "cedant",
    "loss ratio", "actuarial", "exposure", "liability",
]

# Skills from AP/Finance that transfer directly to underwriting support
TRANSFERABLE_SIGNALS = [
    "invoice", "reconciliation", "data entry", "documentation",
    "compliance", "audit", "reporting", "financial analysis",
    "vendor management", "payment processing", "accounts",
    "verification", "month-end", "ledger", "journal",
]

TECH_SIGNALS = [
    "excel", "microsoft excel", "data analysis", "sap", "oracle",
    "sql", "power bi", "tableau", "python", "system",
]

SOFT_SIGNALS = [
    "detail", "analytical", "communication", "organised", "organized",
    "accurate", "deadline", "teamwork", "multitask", "problem solving",
]

# Singapore market salary benchmarks for underwriting roles (monthly SGD, 2025/2026 data)
SALARY_BENCHMARKS = {
    "underwriting assistant": (3500, 5000),
    "underwriting executive": (4000, 6000),
    "underwriting officer": (3800, 5500),
    "underwriting analyst": (4500, 7000),
    "insurance assistant": (3200, 4500),
    "insurance executive": (3800, 5500),
    "claims assistant": (3200, 4500),
    "claims executive": (3800, 5500),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", (text or "").lower())


def _any_hit(signals: list[str], text: str) -> float:
    if not signals:
        return 0.0
    return sum(1 for s in signals if s in text) / len(signals)


def _role_score(title: str, description: str) -> float:
    combined = _norm(f"{title} {description}")
    title_norm = _norm(title)

    title_hits = sum(1 for r in UNDERWRITING_ROLE_TITLES if r in title_norm)
    if title_hits >= 1:
        return 1.0

    if "underwriting" in combined or "underwriter" in combined:
        return 0.90
    if "insurance" in combined:
        return 0.75
    if any(kw in combined for kw in ["claims", "reinsurance", "policy"]):
        return 0.65
    if any(kw in combined for kw in ["risk", "broker"]):
        return 0.50
    return 0.10


# ── Salary filter (reuse from main matcher) ──────────────────────────────────

MIN_SALARY = 4000

def _parse_min_salary(salary_str: str) -> float | None:
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
    salary_str = job.get("salary", "")
    min_sal = _parse_min_salary(salary_str)
    if min_sal is None:
        return True
    return min_sal >= MIN_SALARY


def keyword_match_score(job: dict) -> float:
    title = job.get("title", "")
    desc = job.get("description", "")
    text = _norm(f"{title} {desc} {job.get('company', '')}")

    role_s = _role_score(title, desc)
    transfer_s = _any_hit(TRANSFERABLE_SIGNALS, text)
    tech_s = _any_hit(TECH_SIGNALS, text)
    soft_s = _any_hit(SOFT_SIGNALS, text)

    # Boost: underwriting role with any transferable skill
    if role_s >= 0.65 and transfer_s > 0:
        role_s = min(role_s + 0.05, 1.0)

    score = (role_s * 0.30) + (transfer_s * 0.35) + (tech_s * 0.20) + (soft_s * 0.15)
    return round(score, 4)


# ── Expiring soon & salary benchmark helpers ─────────────────────────────────

def _is_expiring_soon(job: dict) -> bool:
    """Return True if job was posted 11+ days ago (within 3 days of 14-day cutoff)."""
    posted = job.get("posted_date") or job.get("posted") or ""
    if not posted:
        return False
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            posted_dt = datetime.strptime(posted.strip()[:19], fmt)
            days_ago = (datetime.now() - posted_dt).days
            return days_ago >= 11
        except (ValueError, TypeError):
            continue
    return False


def _salary_benchmark(job: dict) -> str:
    """Compare job salary against market benchmarks. Returns label or ''."""
    title_norm = _norm(job.get("title", ""))
    bench = None
    for role, rng in SALARY_BENCHMARKS.items():
        if role in title_norm:
            bench = rng
            break
    if bench is None:
        return ""

    salary_str = (job.get("salary") or "").lower().replace(",", "")
    if not salary_str or "not disclosed" in salary_str:
        return ""

    nums = re.findall(r"[\d]+(?:\.[\d]+)?", salary_str)
    if not nums:
        return ""

    sal_min = float(nums[0])
    sal_max = float(nums[-1]) if len(nums) > 1 else sal_min

    if sal_min >= bench[1]:
        return "Above market"
    if sal_max <= bench[0]:
        return "Below market"
    return "At market"


# ── Analysis ──────────────────────────────────────────────────────────────────

def _analyse_job(job: dict, score: float) -> dict:
    title = job.get("title", "")
    company = job.get("company", "")
    text = _norm(f"{title} {job.get('description', '')}")

    matched_transfer = [s for s in rp.FUNCTIONAL_SKILLS if s.lower() in text]
    matched_tech = [s for s in rp.TECHNICAL_SKILLS if s.lower() in text]

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths = []
    if any(kw in text for kw in ["documentation", "data entry", "processing"]):
        strengths.append(
            f"{rp.TOTAL_YEARS_EXPERIENCE:.0f}+ years of high-volume document processing "
            f"and data accuracy in AP — directly transferable"
        )
    if any(kw in text for kw in ["reconcil", "verification", "audit"]):
        strengths.append(
            "Deep reconciliation and verification background — "
            "core skill for underwriting data checks"
        )
    if any(kw in text for kw in ["compliance", "regulatory", "policy"]):
        strengths.append(
            "Compliance and regulatory awareness from AP statutory board experience"
        )
    if any(kw in text for kw in ["excel", "data", "report", "analysis"]):
        strengths.append(
            "Advanced Excel and data analysis skills from financial reporting"
        )
    if any(kw in text for kw in ["vendor", "client", "stakeholder", "broker"]):
        strengths.append(
            "Strong stakeholder management — vendor liaison experience transfers to broker/client relations"
        )
    if not strengths:
        strengths.append(
            f"{rp.TOTAL_YEARS_EXPERIENCE:.0f}+ years of meticulous financial operations "
            f"— strong foundation for underwriting support"
        )

    # ── Weaknesses / Watch-outs ───────────────────────────────────────────────
    weaknesses = []
    if any(kw in text for kw in ["insurance", "underwriting", "reinsurance"]):
        weaknesses.append(
            "No direct insurance/underwriting experience — "
            "highlight transferable AP skills in cover letter"
        )
    if any(kw in text for kw in ["degree", "bachelor", "university"]):
        weaknesses.append("Role may prefer a degree; candidate holds Diploma in Commerce")
    if any(kw in text for kw in ["certification", "cii", "anziif", "loma"]):
        weaknesses.append(
            "Insurance certification may be preferred — consider CII or ANZIIF qualification"
        )
    if not weaknesses:
        weaknesses.append(
            "Career transition from AP to underwriting — "
            "emphasise transferable skills and willingness to learn"
        )

    # ── Resume tips ───────────────────────────────────────────────────────────
    resume_tips = [
        "Lead with a career-pivot summary: '18+ years financial operations professional "
        "transitioning to insurance underwriting support'",
        "Reframe AP achievements in insurance language: 'verification' → 'risk documentation', "
        "'reconciliation' → 'exposure validation'",
    ]
    if "excel" in text or "data" in text:
        resume_tips.append(
            "Highlight data handling: 'Managed SGD X million in transaction data with 99.9% accuracy'"
        )
    if "team" in text or "support" in text:
        resume_tips.append(
            "Emphasise support role strengths: coordination, prioritisation, deadline management"
        )
    resume_tips.append(
        f"Mirror job keywords in skills section: "
        f"{', '.join((matched_transfer + matched_tech)[:5]) or 'data entry, documentation, compliance, Excel'}"
    )

    # ── Cover letter snippet (career transition emphasis) ───────────────────
    transfer_str = ", ".join(matched_transfer[:3]) if matched_transfer else "document processing, data accuracy, and compliance"
    tech_str = ", ".join(matched_tech[:2]) if matched_tech else "Excel and data analysis"

    pivot_detail = "high-volume document processing, data accuracy, and compliance"
    if any(kw in text for kw in ["reconcil", "verification"]):
        pivot_detail = "reconciliation, verification, and meticulous data validation"
    elif any(kw in text for kw in ["compliance", "regulatory", "policy"]):
        pivot_detail = "regulatory compliance, audit preparation, and policy adherence"
    elif any(kw in text for kw in ["data", "analysis", "report"]):
        pivot_detail = "financial data analysis, reporting, and transaction processing"

    cover_letter = (
        f"Dear Hiring Manager, I am writing to express my strong interest in the {title} "
        f"position at {company}. With {rp.TOTAL_YEARS_EXPERIENCE:.0f}+ years in financial "
        f"operations, including {pivot_detail}, I bring directly transferable skills to "
        f"underwriting support. My career in accounts payable across MNCs and Singapore "
        f"statutory boards has built a rigorous foundation in {transfer_str}. I am eager to "
        f"apply my expertise in {tech_str} and my proven attention to detail to contribute "
        f"meaningfully to your underwriting team."
    )

    return {
        "match_score": score,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:4],
        "relevance_reason": (
            f"This {title} role at {company} can leverage Nurashikin's {rp.TOTAL_YEARS_EXPERIENCE:.0f}+ "
            f"years of financial operations experience — document processing, data accuracy, "
            f"reconciliation, and compliance skills transfer directly to underwriting support."
        ),
        "resume_tips": resume_tips[:5],
        "cover_letter": cover_letter,
        "expiring_soon": _is_expiring_soon(job),
        "salary_benchmark": _salary_benchmark(job),
    }


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
        print(f"[UW Matcher] {salary_filtered} jobs filtered out (salary below SGD {MIN_SALARY:,})")

    matched.sort(key=lambda j: j["match_score"], reverse=True)
    print(
        f"[UW Matcher] {len(matched)} jobs passed the "
        f"{MATCH_THRESHOLD * 100:.0f}% threshold (from {len(jobs)} total)"
    )
    for job in matched:
        job["display_score"] = display_score(job["match_score"])
        job["analysis"]["match_score"] = job["display_score"]
    return matched
