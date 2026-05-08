import re
import json
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import logger
from core.llm_provider import call_llm, safe_parse_json


# ─────────────────────────────────────────────
# DOCUMENT TYPE REGISTRY
# ─────────────────────────────────────────────

DOCUMENT_TYPES = {
    "legal_notice": {
        "label":       "Legal Notice",
        "description": "Formal notice sent before initiating legal proceedings",
        "use_cases":   [
            "deposit disputes", "contract breach", "property damage",
            "unpaid dues", "service failure"
        ]
    },
    "complaint_letter": {
        "label":       "Formal Complaint Letter",
        "description": "Formal complaint to an authority or organisation",
        "use_cases":   [
            "consumer complaints", "workplace grievances",
            "service complaints", "harassment reports"
        ]
    },
    "fir_draft": {
        "label":       "First Information Report (FIR)",
        "description": "First Information Report draft for police filing",
        "use_cases":   [
            "theft", "fraud", "assault", "property crime",
            "cheating", "harassment"
        ]
    }
}

# ─────────────────────────────────────────────
# DOCUMENT TITLE MAPPING
# ─────────────────────────────────────────────

DOCUMENT_TITLE_MAP = {
    "legal_notice":     "Legal Notice",
    "complaint_letter": "Formal Complaint Letter",
    "fir_draft":        "First Information Report (FIR)"
}

# ─────────────────────────────────────────────
# SECTION DEFINITIONS PER DOC TYPE
# ─────────────────────────────────────────────

DOCUMENT_SECTIONS = {
    "legal_notice": [
        "Header",
        "Subject",
        "Facts",
        "Legal Basis",
        "Demand",
        "Closing",
        "Disclaimer"
    ],
    "complaint_letter": [
        "Header",
        "Subject",
        "Complainant Details",
        "Respondent Details",
        "Facts",
        "Relief Sought",
        "Enclosures",
        "Closing",
        "Disclaimer"
    ],
    "fir_draft": [
        "Header",
        "Incident Details",
        "Complainant Details",
        "Accused Details",
        "Facts",
        "Witnesses and Evidence",
        "Offences Applicable",
        "Declaration",
        "Disclaimer"
    ]
}

# ─────────────────────────────────────────────
# PLACEHOLDER STANDARD FORMAT
# ─────────────────────────────────────────────

# All placeholders use UPPER_SNAKE_CASE inside [ ]
PLACEHOLDER_NORMALISATION = {
    # Common inconsistent variants → standard form
    "Sender Name":          "SENDER_NAME",
    "sender name":          "SENDER_NAME",
    "SENDER NAME":          "SENDER_NAME",
    "Recipient Name":       "RECIPIENT_NAME",
    "RECIPIENT NAME":       "RECIPIENT_NAME",
    "recipient name":       "RECIPIENT_NAME",
    "Not Provided":         "NOT_PROVIDED",
    "NOT PROVIDED":         "NOT_PROVIDED",
    "not provided":         "NOT_PROVIDED",
    "Complainant Name":     "COMPLAINANT_NAME",
    "COMPLAINANT NAME":     "COMPLAINANT_NAME",
    "Police Station":       "POLICE_STATION",
    "POLICE STATION":       "POLICE_STATION",
    "Accused Name":         "ACCUSED_NAME",
    "ACCUSED NAME":         "ACCUSED_NAME",
    "Date":                 "DATE",
    "Address":              "ADDRESS",
    "Amount":               "AMOUNT",
    "Subject":              "SUBJECT",
}


# ─────────────────────────────────────────────
# STATIC TEMPLATE ENGINE
# ─────────────────────────────────────────────

def _fill_template(template: str, fields: Dict) -> str:
    """Replace {{FIELD}} placeholders with values from fields dict."""
    for key, value in fields.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    # Replace any unfilled double-brace placeholders with [NOT_PROVIDED]
    template = re.sub(r"\{\{[A-Z_]+\}\}", "[NOT_PROVIDED]", template)
    return template


LEGAL_NOTICE_TEMPLATE = """[SENDER_NAME]
[SENDER_ADDRESS]
Date: {{date}}

TO,
{{recipient_name}}
{{recipient_address}}

SUBJECT: LEGAL NOTICE — {{subject}}

Sir/Madam,

I, {{sender_name}}, residing at {{sender_address}}, hereby serve
you this Legal Notice.

FACTS:
{{facts}}

LEGAL BASIS:
Your actions constitute a breach of {{legal_basis}}.

DEMAND:
You are required to {{demand}} within {{deadline}} days of receipt
of this notice, failing which I shall initiate legal proceedings
without further notice, at your cost and risk.

All rights and remedies are expressly reserved.

Yours faithfully,

{{sender_name}}
Date: {{date}}

---
DISCLAIMER: This is a draft document for guidance purposes only.
Have it reviewed by a qualified lawyer before sending.
Send via registered post with acknowledgement due.
""".strip()


COMPLAINT_LETTER_TEMPLATE = """{{sender_name}}
{{sender_address}}
Contact: {{sender_contact}}
Date: {{date}}

TO,
The {{authority_name}}
{{authority_address}}

SUBJECT: FORMAL COMPLAINT — {{subject}}

Respected Sir/Madam,

I, {{sender_name}}, wish to formally bring the following matter
to your attention.

COMPLAINANT DETAILS:
- Name:    {{sender_name}}
- Address: {{sender_address}}
- Contact: {{sender_contact}}

RESPONDENT DETAILS:
- Name / Organisation: {{respondent_name}}
- Address:             {{respondent_address}}

FACTS:
{{complaint_details}}

RELIEF SOUGHT:
{{relief_sought}}

I request you to investigate this matter and take appropriate
action at the earliest. I am available for further clarification.

Yours sincerely,

{{sender_name}}
Date: {{date}}

ENCLOSURES:
{{enclosures}}

---
DISCLAIMER: This is a draft document for guidance purposes only.
Attach all supporting documents listed under Enclosures.
""".strip()


FIR_DRAFT_TEMPLATE = """TO,
The Station House Officer,
{{police_station}} Police Station,
{{police_station_address}}

SUBJECT: COMPLAINT / FIR — {{offence_type}}

DATE OF INCIDENT:  {{incident_date}}
TIME OF INCIDENT:  {{incident_time}}
PLACE OF INCIDENT: {{incident_place}}

COMPLAINANT DETAILS:
- Name:    {{complainant_name}}
- Address: {{complainant_address}}
- Contact: {{complainant_contact}}

ACCUSED DETAILS:
- Name:    {{accused_name}}
- Address: {{accused_address}}

FACTS OF THE INCIDENT:
{{incident_details}}

WITNESSES:
{{witnesses}}

EVIDENCE AVAILABLE:
{{evidence}}

OFFENCES APPLICABLE:
{{offences_applicable}}

DECLARATION:
I declare that the above information is true and correct to the
best of my knowledge and belief. I request you to register an FIR
and take necessary legal action against the accused.

{{complainant_name}}
Date: {{date}}

---
DISCLAIMER: This is a draft FIR for guidance purposes only.
Present this at your nearest police station. If police refuse to
register, approach the Superintendent of Police or a Magistrate
under Section 156(3) CrPC.
""".strip()


def generate_document_static(
    doc_type:  str,
    user_info: Dict
) -> str:
    """
    Generate a document using static templates.
    No LLM call — instant fallback.
    """
    today = datetime.now().strftime("%d %B %Y")
    user_info.setdefault("date", today)

    if doc_type == "legal_notice":
        return _fill_template(LEGAL_NOTICE_TEMPLATE, user_info)
    if doc_type == "complaint_letter":
        return _fill_template(COMPLAINT_LETTER_TEMPLATE, user_info)
    if doc_type == "fir_draft":
        return _fill_template(FIR_DRAFT_TEMPLATE, user_info)

    raise ValueError(f"Unknown document type: {doc_type}")


# ─────────────────────────────────────────────
# IMPROVED LLM DOCUMENT GENERATOR
# ─────────────────────────────────────────────

def _build_docgen_prompt(
    doc_type:  str,
    user_info: Dict,
    context:   str = ""
) -> str:
    """
    Build a structured document generation prompt.
    Enforces sections, standardised placeholders, no hallucination.
    """
    doc_label  = DOCUMENT_TITLE_MAP.get(doc_type, doc_type.replace("_", " ").title())
    sections   = DOCUMENT_SECTIONS.get(doc_type, [])
    today      = datetime.now().strftime("%d %B %Y")

    # Format available user info
    info_lines = "\n".join(
        f"  {k.replace('_', ' ').upper()}: {v}"
        for k, v in user_info.items()
        if v and str(v).strip()
    ) or "  No specific details provided."

    # Format required sections
    sections_str = "\n".join(f"  - {s}" for s in sections)

    context_block = (
        f"\nRELEVANT LEGAL CONTEXT (use only what applies):\n{context}\n"
        if context.strip() else ""
    )

    return f"""You are a professional legal document drafter. Generate a complete {doc_label}.

TODAY'S DATE: {today}

AVAILABLE INFORMATION:
{info_lines}
{context_block}
REQUIRED SECTIONS (include all of these in order):
{sections_str}

STRICT RULES:
1. Use ONLY the information provided above — never invent facts, names, amounts, or laws.
2. For ANY missing information, write the placeholder in format [FIELD_NAME] using UPPER_SNAKE_CASE.
   Examples: [SENDER_NAME], [COMPLAINANT_ADDRESS], [INCIDENT_DATE], [AMOUNT_CLAIMED]
3. Every section heading must appear on its own line in ALL CAPS followed by a colon.
   Example:  FACTS:
4. Keep language formal, concise, and factual. No emotional language.
5. Do not add any section not listed above.
6. Do not add commentary, explanation, or notes outside the document itself.
7. End the document with a DISCLAIMER section stating this is a draft for review.
8. Use numbered lists only for sequential steps. Use bullet points for factual items.
9. Minimum document length: 200 words.

OUTPUT: Return ONLY the document text. No explanation before or after.
"""


def generate_document_llm(
    doc_type:  str,
    user_info: Dict,
    context:   str = ""
) -> str:
    """
    Generate a legal document using local Ollama.
    Returns plain text document or falls back to static template.
    """
    logger.info(f"[DocGen] Generating {doc_type} via LLM...")

    prompt = _build_docgen_prompt(doc_type, user_info, context)

    try:
        doc_text = call_llm(
            prompt      = prompt,
            max_tokens  = 1500,
            expect_json = False
        )

        # Quality gate
        if len(doc_text.strip().split()) < 80:
            logger.warning(
                "[DocGen] LLM returned document below minimum length "
                f"({len(doc_text.split())} words) — falling back to template."
            )
            return generate_document_static(doc_type, user_info)

        # Reject if LLM returned JSON or code instead of document
        stripped = doc_text.strip()
        if stripped.startswith("{") or stripped.startswith("```"):
            logger.warning(
                "[DocGen] LLM returned non-document output — "
                "falling back to template."
            )
            return generate_document_static(doc_type, user_info)

        logger.info(
            f"[DocGen] LLM document generated — "
            f"{len(doc_text.split())} words."
        )
        return doc_text.strip()

    except Exception as e:
        logger.error(f"[DocGen] LLM failed: {e} — using static template.")
        return generate_document_static(doc_type, user_info)


# ─────────────────────────────────────────────
# FIELD EXTRACTION
# ─────────────────────────────────────────────

def _build_extraction_prompt(
    situation: str,
    doc_type:  str
) -> str:
    doc_label = DOCUMENT_TITLE_MAP.get(doc_type, doc_type)

    field_map = {
        "legal_notice": [
            "sender_name", "sender_address", "recipient_name",
            "recipient_address", "subject", "facts",
            "legal_basis", "demand", "deadline"
        ],
        "complaint_letter": [
            "sender_name", "sender_address", "sender_contact",
            "respondent_name", "respondent_address",
            "authority_name", "authority_address",
            "subject", "complaint_details", "relief_sought", "enclosures"
        ],
        "fir_draft": [
            "complainant_name", "complainant_address", "complainant_contact",
            "accused_name", "accused_address", "offence_type",
            "incident_date", "incident_time", "incident_place",
            "incident_details", "witnesses", "evidence",
            "offences_applicable", "police_station", "police_station_address"
        ]
    }

    fields     = field_map.get(doc_type, [])
    fields_str = "\n".join(
        f'  "{f}": "<extracted value or empty string>"'
        for f in fields
    )

    return f"""Extract information for a {doc_label} from this situation.

SITUATION:
{situation}

Return ONLY this JSON. Use empty string "" for missing fields.
Never invent or assume values not stated in the situation.

{{
{fields_str}
}}"""


def extract_document_fields(
    situation: str,
    doc_type:  str
) -> Dict:
    """
    Extract structured fields from a free-text situation description.
    Falls back to safe defaults on failure.
    """
    logger.info(f"[DocGen] Extracting fields for {doc_type}...")

    default_fields = {
        "legal_notice": {
            "sender_name": "", "sender_address": "",
            "recipient_name": "", "recipient_address": "",
            "subject": "Legal Dispute",
            "facts": situation[:500],
            "legal_basis": "applicable laws and agreements",
            "demand": "resolve this matter immediately",
            "deadline": "15"
        },
        "complaint_letter": {
            "sender_name": "", "sender_address": "", "sender_contact": "",
            "respondent_name": "", "respondent_address": "",
            "authority_name": "Concerned Authority", "authority_address": "",
            "subject": "Formal Complaint",
            "complaint_details": situation[:500],
            "relief_sought": "appropriate remedial action",
            "enclosures": "supporting documents as applicable"
        },
        "fir_draft": {
            "complainant_name": "", "complainant_address": "",
            "complainant_contact": "", "accused_name": "",
            "accused_address": "", "offence_type": "criminal offence",
            "incident_date": "", "incident_time": "",
            "incident_place": "",
            "incident_details": situation[:500],
            "witnesses": "", "evidence": "",
            "offences_applicable": "as applicable under IPC",
            "police_station": "", "police_station_address": ""
        }
    }

    fallback = default_fields.get(doc_type, {"details": situation})
    prompt   = _build_extraction_prompt(situation, doc_type)

    try:
        raw       = call_llm(prompt, max_tokens=512, expect_json=True)
        extracted = safe_parse_json(raw, fallback)

        # Fill missing keys from fallback
        for k, v in fallback.items():
            if k not in extracted or not str(extracted[k]).strip():
                extracted[k] = v

        logger.info(f"[DocGen] Extracted {len(extracted)} fields.")
        return extracted

    except Exception as e:
        logger.warning(f"[DocGen] Field extraction failed: {e} — using defaults.")
        return fallback


# ─────────────────────────────────────────────
# PLACEHOLDER EXTRACTOR + NORMALISER
# ─────────────────────────────────────────────

def _normalise_placeholder(raw: str) -> str:
    """
    Normalise a raw placeholder string to UPPER_SNAKE_CASE.
    'sender name' → 'SENDER_NAME'
    'NOT PROVIDED' → 'NOT_PROVIDED'
    """
    # Check known normalisation map first
    if raw in PLACEHOLDER_NORMALISATION:
        return PLACEHOLDER_NORMALISATION[raw]

    # Generic normalisation: upper + spaces/hyphens → underscores
    normalised = raw.strip().upper().replace(" ", "_").replace("-", "_")
    # Collapse multiple underscores
    normalised = re.sub(r"_+", "_", normalised)
    return normalised


def extract_placeholders(text: str) -> List[str]:
    """
    Extract and normalise all [PLACEHOLDER] tokens from document text.
    Returns deduplicated list preserving first-appearance order.
    """
    raw_matches = re.findall(r'\[([^\[\]\n]{1,60})\]', text)
    seen        = set()
    ordered     = []

    for raw in raw_matches:
        normalised = _normalise_placeholder(raw.strip())
        if normalised and normalised not in seen:
            seen.add(normalised)
            ordered.append(normalised)

    return ordered


# ─────────────────────────────────────────────
# TEXT CLEANER
# ─────────────────────────────────────────────

def clean_document_text(text: str) -> str:
    """
    Clean and normalise raw document text for frontend rendering.
    - Convert escaped newlines
    - Strip trailing spaces per line
    - Collapse 3+ blank lines into 2
    - Normalise placeholder casing inline
    """
    # Convert escaped sequences
    text = text.replace("\\n", "\n")
    text = text.replace("\\t", "    ")

    # Normalise placeholders inline:
    # Replace [anything] with [UPPER_SNAKE_CASE] version
    def _replace_placeholder(m: re.Match) -> str:
        inner = m.group(1).strip()
        return f"[{_normalise_placeholder(inner)}]"

    text = re.sub(r'\[([^\[\]\n]{1,60})\]', _replace_placeholder, text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]

    # Collapse 3+ consecutive blank lines → max 2
    cleaned   = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)

    return "\n".join(cleaned).strip() + "\n"


# ─────────────────────────────────────────────
# SECTION SEGMENTOR
# ─────────────────────────────────────────────

def segment_into_sections(
    text:     str,
    doc_type: str
) -> List[Dict]:
    """
    Split cleaned document text into named sections.
    Detects ALL-CAPS section headings followed by colon.
    Returns list of {heading, content} dicts.

    Falls back to one section containing full text if no
    headings are detected.
    """
    # Pattern: line that is ALL CAPS (with spaces/underscores) ending in colon
    heading_pattern = re.compile(
        r'^([A-Z][A-Z\s\(\)\/]{2,}):?\s*$',
        re.MULTILINE
    )

    matches = list(heading_pattern.finditer(text))

    if not matches:
        # No headings found — return as single body section
        return [{"heading": "Document", "content": text.strip()}]

    sections = []

    for i, match in enumerate(matches):
        heading     = match.group(1).strip().rstrip(":")
        start       = match.end()
        end         = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content     = text[start:end].strip()

        if content or heading.upper() in ("DISCLAIMER", "DECLARATION"):
            sections.append({
                "heading": heading.title(),
                "content": content
            })

    # Always ensure Disclaimer is last if present
    non_disclaimer = [s for s in sections if "disclaimer" not in s["heading"].lower()]
    disclaimer     = [s for s in sections if "disclaimer" in s["heading"].lower()]
    return non_disclaimer + disclaimer


# ─────────────────────────────────────────────
# QUALITY CHECKER
# ─────────────────────────────────────────────

def _quality_check(
    text:     str,
    doc_type: str
) -> Dict:
    """
    Run quality checks on generated document.
    Returns {passed, issues, word_count}.
    """
    issues     = []
    word_count = len(text.split())

    # Minimum length
    if word_count < 80:
        issues.append(f"Document too short: {word_count} words (minimum 80).")

    # Must contain at least one section heading
    if not re.search(r'^[A-Z]{3,}', text, re.MULTILINE):
        issues.append("No section headings detected.")

    # Should not contain JSON artifacts
    if text.strip().startswith("{") or "```" in text:
        issues.append("Document contains code/JSON artifacts.")

    # Should not be mostly placeholders
    placeholder_count = len(re.findall(r'\[[A-Z_]+\]', text))
    if placeholder_count > 12:
        issues.append(
            f"High placeholder count ({placeholder_count}) — "
            "situation may lack sufficient detail."
        )

    return {
        "passed":     len(issues) == 0,
        "issues":     issues,
        "word_count": word_count
    }


# ─────────────────────────────────────────────
# STRUCTURED RESPONSE FORMATTER
# ─────────────────────────────────────────────

def format_document_response(
    raw_result: Dict,
    doc_type:   str
) -> Dict:
    """
    Convert raw generate_legal_document() output into a
    structured, frontend-ready response with sections.
    """
    raw_text     = raw_result.get("document", "")
    cleaned_text = clean_document_text(raw_text)
    sections     = segment_into_sections(cleaned_text, doc_type)
    placeholders = extract_placeholders(cleaned_text)
    title        = DOCUMENT_TITLE_MAP.get(
        doc_type, doc_type.replace("_", " ").title()
    )
    quality      = _quality_check(cleaned_text, doc_type)

    return {
        "status":          raw_result.get("status", "success"),
        "doc_type":        doc_type,
        "generated_date":  raw_result.get(
            "generated_date",
            datetime.now().strftime("%d %B %Y")
        ),
        "generation_mode": raw_result.get("generation_mode", "static"),
        "word_count":      quality["word_count"],
        "quality": {
            "passed": quality["passed"],
            "issues": quality["issues"]
        },
        "disclaimer": raw_result.get(
            "disclaimer",
            "This document is a draft for guidance only. "
            "Review with a qualified lawyer before use."
        ),
        "document": {
            "type":         doc_type,
            "title":        title,
            "sections":     sections,
            "full_text":    cleaned_text,
            "placeholders": placeholders
        }
    }


# ─────────────────────────────────────────────
# STRUCTURED FALLBACK
# ─────────────────────────────────────────────

def build_structured_fallback(doc_type: str) -> Dict:
    """
    Return a fully structured fallback when generation fails.
    Frontend-safe — always returns correct shape with sections.
    """
    title = DOCUMENT_TITLE_MAP.get(
        doc_type, doc_type.replace("_", " ").title()
    )
    today = datetime.now().strftime("%d %B %Y")

    fallback_sections = [
        {
            "heading": "Header",
            "content": (
                f"[SENDER_NAME]\n"
                f"[SENDER_ADDRESS]\n"
                f"Date: {today}"
            )
        },
        {
            "heading": "Subject",
            "content": "RE: [SUBJECT]"
        },
        {
            "heading": "Facts",
            "content": (
                "[FACTS_OF_THE_MATTER]\n\n"
                "Please provide your situation details to generate "
                "a complete document."
            )
        },
        {
            "heading": "Relief Sought",
            "content": "[RELIEF_OR_DEMAND]"
        },
        {
            "heading": "Closing",
            "content": (
                "Yours faithfully,\n\n"
                "[SENDER_NAME]\n"
                f"Date: {today}"
            )
        },
        {
            "heading": "Disclaimer",
            "content": (
                "This is a placeholder document only. "
                "Provide more details for a complete draft. "
                "Consult a qualified lawyer before use."
            )
        }
    ]

    full_text = "\n\n".join(
        f"{s['heading'].upper()}:\n{s['content']}"
        for s in fallback_sections
    ) + "\n"

    placeholders = extract_placeholders(full_text)

    return {
        "status":          "fallback",
        "doc_type":        doc_type,
        "generated_date":  today,
        "generation_mode": "fallback",
        "word_count":      len(full_text.split()),
        "quality": {
            "passed": False,
            "issues": ["Document generation failed — fallback template used."]
        },
        "disclaimer": (
            "This is a placeholder document only. "
            "Consult a qualified lawyer for proper drafting."
        ),
        "document": {
            "type":         doc_type,
            "title":        title,
            "sections":     fallback_sections,
            "full_text":    full_text,
            "placeholders": placeholders
        }
    }


# ─────────────────────────────────────────────
# MASTER DOCUMENT GENERATOR
# ─────────────────────────────────────────────

def generate_legal_document(
    doc_type:  str,
    situation: str,
    user_info: Optional[Dict] = None,
    context:   str            = "",
    use_llm:   bool           = True
) -> Dict:
    """
    Master document generation function.

    Pipeline:
    1. Validate doc_type
    2. Extract fields from situation (1 LLM call) OR use user_info
    3. Generate document (1 LLM call) OR static template
    4. Return raw result dict

    Max LLM calls: 2 (extraction + generation)
    With use_llm=False: 0 LLM calls
    With user_info provided: 1 LLM call (generation only)
    """
    if doc_type not in DOCUMENT_TYPES:
        raise ValueError(
            f"Unknown document type '{doc_type}'. "
            f"Valid: {list(DOCUMENT_TYPES.keys())}"
        )

    logger.info(
        f"[DocGen] Request — type: {doc_type} | "
        f"use_llm: {use_llm} | "
        f"user_info provided: {user_info is not None}"
    )

    # Step 1: Determine fields
    if user_info and len(user_info) >= 3:
        fields = user_info
        logger.info("[DocGen] Using provided user_info fields.")
    elif use_llm:
        fields = extract_document_fields(situation, doc_type)
    else:
        fields = {"details": situation, "facts": situation[:500]}

    # Step 2: Generate
    if use_llm:
        document_text = generate_document_llm(doc_type, fields, context)
    else:
        document_text = generate_document_static(doc_type, fields)

    today = datetime.now().strftime("%d %B %Y")

    return {
        "document":        document_text,
        "generated_date":  today,
        "generation_mode": "llm" if use_llm else "static",
        "word_count":      len(document_text.split()),
        "fields_used":     fields,
        "disclaimer": (
            "This document is a draft generated for guidance purposes only. "
            "Review with a qualified lawyer before use."
        )
    }