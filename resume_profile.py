"""
Resume profile — loads from RESUME_PROFILE environment variable (JSON).
Set this in .env locally, or as a GitHub Secret for cloud runs.
"""

import os
import json

_raw = os.getenv("RESUME_PROFILE", "")
if not _raw:
    raise EnvironmentError(
        "RESUME_PROFILE environment variable is not set.\n"
        "Add it to your .env file (local) or GitHub Secrets (cloud)."
    )

_data = json.loads(_raw)

CANDIDATE_NAME        = _data["CANDIDATE_NAME"]
CANDIDATE_EMAIL       = _data["CANDIDATE_EMAIL"]
CANDIDATE_LOCATION    = _data["CANDIDATE_LOCATION"]
TECHNICAL_SKILLS      = _data["TECHNICAL_SKILLS"]
FUNCTIONAL_SKILLS     = _data["FUNCTIONAL_SKILLS"]
SOFT_SKILLS           = _data["SOFT_SKILLS"]
LANGUAGES             = _data["LANGUAGES"]
EDUCATION             = _data["EDUCATION"]
TOTAL_YEARS_EXPERIENCE = _data["TOTAL_YEARS_EXPERIENCE"]
TARGET_ROLES          = _data["TARGET_ROLES"]
INDUSTRY_EXPERIENCE   = _data["INDUSTRY_EXPERIENCE"]

ALL_SKILLS_FLAT = (
    [s.lower() for s in TECHNICAL_SKILLS]
    + [s.lower() for s in FUNCTIONAL_SKILLS]
    + [s.lower() for s in SOFT_SKILLS]
)
