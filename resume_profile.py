"""
Resume profile loader.

Data is loaded exclusively from the RESUME_PROFILE environment variable (JSON).
- Local: set RESUME_PROFILE in your .env file
- GitHub Actions: set RESUME_PROFILE as a repository secret

This file contains NO personal data and is safe to commit.
"""

from __future__ import annotations
import os
import json

_raw = os.getenv("RESUME_PROFILE", "")
if not _raw:
    raise EnvironmentError(
        "RESUME_PROFILE environment variable is not set.\n"
        "  Local:  add RESUME_PROFILE=<json> to your .env file\n"
        "  GitHub: add RESUME_PROFILE as a repository secret"
    )

try:
    _data = json.loads(_raw)
except json.JSONDecodeError as e:
    raise EnvironmentError(f"RESUME_PROFILE is not valid JSON: {e}")

CANDIDATE_NAME         = _data["CANDIDATE_NAME"]
CANDIDATE_EMAIL        = _data["CANDIDATE_EMAIL"]
CANDIDATE_LOCATION     = _data["CANDIDATE_LOCATION"]
TOTAL_YEARS_EXPERIENCE = _data["TOTAL_YEARS_EXPERIENCE"]
TARGET_ROLES           = _data["TARGET_ROLES"]
TECHNICAL_SKILLS       = _data["TECHNICAL_SKILLS"]
FUNCTIONAL_SKILLS      = _data["FUNCTIONAL_SKILLS"]
SOFT_SKILLS            = _data["SOFT_SKILLS"]
LANGUAGES              = _data["LANGUAGES"]
EDUCATION              = _data["EDUCATION"]
INDUSTRY_EXPERIENCE    = _data["INDUSTRY_EXPERIENCE"]

ALL_SKILLS_FLAT = (
    [s.lower() for s in TECHNICAL_SKILLS]
    + [s.lower() for s in FUNCTIONAL_SKILLS]
    + [s.lower() for s in SOFT_SKILLS]
)
