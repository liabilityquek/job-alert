"""
Resume profile for Nurashikin Buang.

Data is hardcoded here since this is a private repository.
Optionally override any field via the RESUME_PROFILE env var (JSON).
"""

from __future__ import annotations
import os
import json

# ── Hardcoded defaults (based on parsed resume) ──────────────────────────────

_DEFAULTS: dict = {
    "CANDIDATE_NAME":        "Nurashikin Buang",
    "CANDIDATE_EMAIL":       "withlovenora@gmail.com",
    "CANDIDATE_LOCATION":    "Singapore",
    "TOTAL_YEARS_EXPERIENCE": 18,

    "TARGET_ROLES": [
        "accounts payable",
        "AP officer",
        "AP executive",
        "finance executive",
        "accounts executive",
        "accounts officer",
        "finance officer",
        "accounting executive",
        "AP manager",
        "finance manager",
    ],

    "TECHNICAL_SKILLS": [
        "Oracle Fusion Cloud",
        "SAP",
        "SAP FI",
        "SAP Concur",
        "Microsoft Excel",
        "Microsoft Office",
        "Workday",
        "NetSuite",
        "IMOS",
        "QuickBooks",
    ],

    "FUNCTIONAL_SKILLS": [
        "Accounts Payable",
        "Invoice Processing",
        "Vendor Management",
        "Reconciliation",
        "Bank Reconciliation",
        "Vendor SOA Reconciliation",
        "Intercompany Reconciliation",
        "3-Way Match",
        "Month-End Closing",
        "General Ledger",
        "Journal Entries",
        "Withholding Tax",
        "Payment Processing",
        "Process Improvement",
        "Audit Preparation",
        "Compliance",
        "APAC Operations",
        "Cash Flow Management",
        "Fixed Assets",
        "Expense Claims",
    ],

    "SOFT_SKILLS": [
        "Attention to detail",
        "Analytical",
        "Team player",
        "Communication",
        "Organised",
        "Deadline-driven",
        "Accuracy",
        "Mentoring",
    ],

    "LANGUAGES": ["English", "Malay"],

    "EDUCATION": [
        {
            "qualification": "Diploma in Commerce",
            "institution":   "Singapore Polytechnic",
            "year":          "1999",
        }
    ],

    "INDUSTRY_EXPERIENCE": [
        "Logistics / Shipping (DP World)",
        "Government / Statutory Board",
        "Manufacturing",
        "MNCs",
        "Singapore SMEs",
    ],
}

# ── Optional env-var override ─────────────────────────────────────────────────
# If RESUME_PROFILE is set (e.g. via GitHub Secret), it merges on top of the
# defaults above. This is optional — the hardcoded defaults work on their own.

_env_raw = os.getenv("RESUME_PROFILE", "")
if _env_raw:
    try:
        _override = json.loads(_env_raw)
        _DEFAULTS.update(_override)
    except json.JSONDecodeError as _e:
        print(f"[resume_profile] Warning: RESUME_PROFILE env var is invalid JSON ({_e}). "
              "Using hardcoded defaults.")

# ── Module-level exports ──────────────────────────────────────────────────────

CANDIDATE_NAME         = _DEFAULTS["CANDIDATE_NAME"]
CANDIDATE_EMAIL        = _DEFAULTS["CANDIDATE_EMAIL"]
CANDIDATE_LOCATION     = _DEFAULTS["CANDIDATE_LOCATION"]
TOTAL_YEARS_EXPERIENCE = _DEFAULTS["TOTAL_YEARS_EXPERIENCE"]
TARGET_ROLES           = _DEFAULTS["TARGET_ROLES"]
TECHNICAL_SKILLS       = _DEFAULTS["TECHNICAL_SKILLS"]
FUNCTIONAL_SKILLS      = _DEFAULTS["FUNCTIONAL_SKILLS"]
SOFT_SKILLS            = _DEFAULTS["SOFT_SKILLS"]
LANGUAGES              = _DEFAULTS["LANGUAGES"]
EDUCATION              = _DEFAULTS["EDUCATION"]
INDUSTRY_EXPERIENCE    = _DEFAULTS["INDUSTRY_EXPERIENCE"]

ALL_SKILLS_FLAT = (
    [s.lower() for s in TECHNICAL_SKILLS]
    + [s.lower() for s in FUNCTIONAL_SKILLS]
    + [s.lower() for s in SOFT_SKILLS]
)
