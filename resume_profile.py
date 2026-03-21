"""
Resume profile for Nurashikin Buang — pre-extracted from PDF.
This is the baseline used for all job matching.
"""

CANDIDATE_NAME = "Nurashikin Buang"
CANDIDATE_EMAIL = "withlovenora@gmail.com"
CANDIDATE_LOCATION = "Singapore"

# ── Technical Skills ──────────────────────────────────────────────────────────
TECHNICAL_SKILLS = [
    "SAP", "Oracle Fusion Cloud", "Oracle Fusion", "Workday", "IMOS",
    "Microsoft Office", "ServiceNow", "SAP Concur", "Cargo Runner",
    "Danaos", "Vendor@gov", "ERP", "CONCUR",
]

# ── Functional / Domain Skills ────────────────────────────────────────────────
FUNCTIONAL_SKILLS = [
    "accounts payable", "account payable", "AP", "invoice processing",
    "3-way matching", "three-way matching", "vendor management",
    "vendor master data", "vendor onboarding", "reconciliation",
    "bank reconciliation", "statement of account", "SOA",
    "journal entries", "GL entries", "general ledger",
    "month-end close", "month end", "audit", "audit preparation",
    "cash flow", "cash flow forecasting", "intercompany transactions",
    "intercompany", "withholding tax", "foreign exchange", "FX",
    "payment processing", "TT payment", "GIRO", "cheque payment",
    "expense reports", "staff claims", "petty cash",
    "procurement", "financial reporting", "accruals",
    "compliance", "internal controls", "UAT testing",
    "process improvement", "automation", "offshore coordination",
]

# ── Soft Skills ───────────────────────────────────────────────────────────────
SOFT_SKILLS = [
    "interpersonal", "teamwork", "analytical", "critical thinking",
    "problem solving", "resilience", "empathy", "emotional intelligence",
    "time management", "attention to detail",
]

# ── Languages ─────────────────────────────────────────────────────────────────
LANGUAGES = ["English", "Malay", "Mandarin"]

# ── Education ─────────────────────────────────────────────────────────────────
EDUCATION = {
    "institution": "Kaplan Higher Education Institute Singapore",
    "qualification": "Diploma in Commerce",
}

# ── Work Experience (chronological, most recent first) ────────────────────────
WORK_EXPERIENCE = [
    {
        "company": "DP World APAC",
        "title": "APAC Account Payable Officer",
        "duration": "Sep 2023 – Present",
        "years": 1.5,
        "highlights": [
            "Oracle Fusion Cloud ERP integration and UAT testing",
            "ServiceNow vendor onboarding and master data management",
            "Multi-currency payments, FX adjustments, withholding tax compliance",
            "Cash flow forecasting, intercompany transactions",
            "APAC-wide AP operations and offshore team mentorship",
            "Process improvement and automation initiatives",
        ],
    },
    {
        "company": "Eastern Pacific Shipping Pte Ltd",
        "title": "Accounts Payable Executive",
        "duration": "Sep 2022 – Sep 2023",
        "years": 1.0,
        "highlights": [
            "AP for shipping vessels — timely vendor payments",
            "3-way matching of e-invoices and IMOS claims",
            "Vendor SOA reconciliation",
        ],
    },
    {
        "company": "U.S. Soybean Export Council",
        "title": "Accounts Payable Executive",
        "duration": "Apr 2022 – Jun 2022",
        "years": 0.2,
        "highlights": [
            "SAP Concur expense processing for SEA region",
            "Vendor and consultant expense reviews",
        ],
    },
    {
        "company": "Dormakaba Production GmbH",
        "title": "Accounts Payable Executive",
        "duration": "May 2021 – Mar 2022",
        "years": 0.8,
        "highlights": [
            "Invoice and claims processing",
            "Vendor reconciliation and payment preparation",
        ],
    },
    {
        "company": "IMDA Singapore",
        "title": "Accounts Payable Executive",
        "duration": "Jan 2020 – Apr 2021",
        "years": 1.3,
        "highlights": [
            "Vendor@gov e-invoice processing",
            "Funding claims and procurement invoice verification",
            "SAP vendor master maintenance",
            "Month-end close and audit schedules",
        ],
    },
    {
        "company": "JTC Corporation",
        "title": "Accounts Payable Executive",
        "duration": "Mar 2018 – Dec 2019",
        "years": 1.8,
        "highlights": [
            "High-volume staff claims (transport, overseas, petty cash, assets)",
            "SAP vendor master maintenance",
            "Process improvement proposals",
        ],
    },
    {
        "company": "Toa Corporation",
        "title": "Accounts Payable Executive",
        "duration": "Jan 2015 – Aug 2017",
        "years": 2.6,
        "highlights": [
            "Inter-company billing, GL adjustment entries",
            "Audit liaison with SG & Japan auditors",
            "Vendor master maintenance, SOA queries",
        ],
    },
    {
        "company": "Citrus Leaves",
        "title": "Account Executive",
        "duration": "Jun 2005 – Dec 2014",
        "years": 9.5,
        "highlights": [
            "Accounts and billing management",
            "Purchase/delivery orders, invoicing, stock management",
        ],
    },
]

# ── Total years of experience ─────────────────────────────────────────────────
TOTAL_YEARS_EXPERIENCE = sum(e["years"] for e in WORK_EXPERIENCE)  # ~18+ years

# ── Target job roles (search keywords) ───────────────────────────────────────
TARGET_ROLES = [
    "Accounts Payable",
    "AP Officer",
    "AP Executive",
    "Finance Executive",
    "Finance Officer",
    "Accounting Executive",
    "Accounts Executive",
    "AP Manager",
    "Finance Manager",
    "Accounts Manager",
    "Senior AP",
    "Senior Accounts Payable",
]

# ── Industries with domain experience ────────────────────────────────────────
INDUSTRY_EXPERIENCE = [
    "logistics", "shipping", "maritime", "government", "statutory board",
    "manufacturing", "trade", "APAC", "multinational",
]

# ── All skills combined (for keyword matching) ────────────────────────────────
ALL_SKILLS_FLAT = (
    [s.lower() for s in TECHNICAL_SKILLS]
    + [s.lower() for s in FUNCTIONAL_SKILLS]
    + [s.lower() for s in SOFT_SKILLS]
)
