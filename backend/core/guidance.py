from typing import Dict
from utils.logger import logger


# ─────────────────────────────────────────────
# INTENT → LEGAL DOMAIN MAPPER
# ─────────────────────────────────────────────

INTENT_DOMAIN_MAP = {
    "tenant_rights":       "Tenant and Landlord Law",
    "contract_analysis":   "Contract Law",
    "contract_comparison": "Contract Law",
    "consumer_rights":     "Consumer Protection Law",
    "employment_law":      "Employment and Labour Law",
    "criminal_law":        "Criminal Law and Procedure",
    "legal_notice":        "Civil Legal Procedure",
    "document_generation": "Legal Documentation",
    "general_legal":       "General Legal Guidance"
}


# ─────────────────────────────────────────────
# STATIC FALLBACK LIBRARY
# ─────────────────────────────────────────────

STATIC_GUIDANCE = {
    "tenant_rights": {
        "rights": [
            "Right to a habitable and safe living space",
            "Right to privacy — landlord must give notice before entry",
            "Right to receive an itemised statement for any deposit deductions",
            "Right to protection against illegal eviction and lockouts",
            "Right to withhold rent if landlord fails habitability duties"
        ],
        "steps": [
            "Document all issues with dated photos and written records",
            "Send a formal written notice to your landlord",
            "Give the landlord reasonable time to respond (14–30 days)",
            "Contact your local housing authority if unresolved",
            "Consult a tenant rights lawyer for eviction or deposit disputes",
            "File in small claims court for deposits under the threshold"
        ],
        "documents": [
            "Signed lease or rental agreement",
            "All written communications with the landlord",
            "Photographic or video evidence of the issue",
            "Receipts for any repair costs you paid",
            "Bank records showing rent payments",
            "Move-in and move-out inspection reports"
        ]
    },
    "contract_analysis": {
        "rights": [
            "Right to understand all terms before signing",
            "Right to negotiate or reject unfair clauses",
            "Right to seek independent legal advice before execution",
            "Right to a copy of the signed contract",
            "Right to challenge grossly disproportionate penalty clauses"
        ],
        "steps": [
            "Read every clause carefully — do not rely on verbal summaries",
            "Identify all obligations, deadlines, and penalty clauses",
            "Flag any ambiguous language for clarification in writing",
            "Negotiate removal or modification of unfair terms",
            "Have a lawyer review contracts involving large sums",
            "Ensure all agreed changes are written into the contract"
        ],
        "documents": [
            "Full contract with all schedules and annexures",
            "Prior drafts showing negotiation changes",
            "Written correspondence about contract terms",
            "Identity documents of all signing parties",
            "Proof of consideration (payment, delivery receipts)",
            "Any related licences or third-party approvals"
        ]
    },
    "consumer_rights": {
        "rights": [
            "Right to goods of satisfactory quality and fit for purpose",
            "Right to a full refund for defective products within warranty",
            "Right to accurate product descriptions and pricing",
            "Right to protection against unfair trade practices",
            "Right to file a complaint with consumer protection agencies"
        ],
        "steps": [
            "Gather proof of purchase — receipt, invoice, or bank statement",
            "Document the defect with photos or videos",
            "Contact the seller in writing for repair, replacement, or refund",
            "Escalate to the manufacturer if seller refuses",
            "File a complaint with your consumer protection body",
            "Consider small claims court for eligible disputes"
        ],
        "documents": [
            "Original receipt or proof of purchase",
            "Warranty card or certificate",
            "Written complaint letters sent to the seller",
            "Photographs or videos of the defective product",
            "Bank or credit card statements showing payment",
            "Product description at time of purchase"
        ]
    },
    "employment_law": {
        "rights": [
            "Right to a written employment contract",
            "Right to protection against wrongful or discriminatory termination",
            "Right to file a workers compensation claim without retaliation",
            "Right to receive all earned wages and benefits on termination",
            "Right to a safe working environment free from harassment"
        ],
        "steps": [
            "Secure copies of your employment contract and amendments",
            "Document all incidents with dates, witnesses, and evidence",
            "Send a formal grievance letter to HR or management",
            "File a complaint with your national labour board if unresolved",
            "Consult an employment attorney promptly",
            "Preserve all emails and performance reviews as evidence"
        ],
        "documents": [
            "Employment contract and offer letters",
            "Pay slips and tax records",
            "Performance reviews and disciplinary notices",
            "Termination letter or notice",
            "All relevant workplace communications",
            "Non-compete or NDA agreements if applicable"
        ]
    },
    "criminal_law": {
        "rights": [
            "Right to file an FIR for any cognizable offence",
            "Right to be informed of the grounds of arrest",
            "Right to legal representation at all stages",
            "Right to remain silent and not self-incriminate",
            "Right to bail for bailable offences"
        ],
        "steps": [
            "Visit the nearest police station and request to file an FIR",
            "If refused, approach the Superintendent of Police in writing",
            "As a last resort, file a private complaint before a Magistrate",
            "Retain a copy of the FIR acknowledgement receipt",
            "Engage a criminal lawyer immediately",
            "Preserve all physical evidence and witness details"
        ],
        "documents": [
            "Written complaint describing the offence in detail",
            "Identity proof of the complainant",
            "Physical evidence: photos, videos, objects",
            "List of witnesses with contact information",
            "Medical reports if there is physical injury",
            "Acknowledgement copy of the filed FIR"
        ]
    },
    "legal_notice": {
        "rights": [
            "Right to send a legal notice before initiating proceedings",
            "Right to demand a response within a specified deadline",
            "Right to claim notice costs in subsequent litigation",
            "Right to use the notice as evidence of prior communication"
        ],
        "steps": [
            "Draft the notice stating facts, legal basis, and remedy",
            "Set a response deadline — typically 15 to 30 days",
            "Send via registered post or courier with delivery confirmation",
            "Retain the signed notice and proof of dispatch",
            "Proceed with legal action if no response received",
            "Engage a lawyer for formal disputes"
        ],
        "documents": [
            "Signed legal notice with all factual details",
            "Registered post receipt or courier tracking proof",
            "Identity proof of the sender",
            "Supporting documents referenced in the notice",
            "Prior correspondence establishing the dispute history"
        ]
    },
    "document_generation": {
        "rights": [
            "Right to draft and send legal notices without a lawyer",
            "Right to file complaints with authorities personally",
            "Right to represent yourself in small claims proceedings"
        ],
        "steps": [
            "Identify the exact document type needed",
            "Gather all factual details: parties, dates, amounts, events",
            "Use clear and formal language — avoid emotional statements",
            "Have the document reviewed by a lawyer before sending",
            "Send via a traceable method and retain proof of delivery"
        ],
        "documents": [
            "Factual summary of the dispute or situation",
            "Identity documents of all parties",
            "Supporting evidence for all claims",
            "Prior correspondence related to the matter"
        ]
    },
    "general_legal": {
        "rights": [
            "Right to access legal information and advice",
            "Right to consult a lawyer before taking legal action",
            "Right to legal aid if you cannot afford representation",
            "Right to fair treatment in all legal proceedings"
        ],
        "steps": [
            "Clearly define the legal issue you are facing",
            "Research the relevant laws that apply",
            "Consult a qualified lawyer in the relevant practice area",
            "Document all facts, dates, and communications",
            "Understand the statutes of limitation that apply"
        ],
        "documents": [
            "All documents relevant to your specific situation",
            "Identity proof",
            "Written record of all events in chronological order",
            "Any prior legal correspondence"
        ]
    }
}


# ─────────────────────────────────────────────
# PROCESS GUIDANCE FROM PIPELINE OUTPUT
# ─────────────────────────────────────────────

def process_guidance_from_pipeline(
    guidance_raw: Dict,
    intent: str
) -> Dict:
    """
    Validate the guidance block from the unified pipeline.
    Fills thin or missing sections from the static library.
    No LLM call — purely post-processing.
    """
    static = STATIC_GUIDANCE.get(intent, STATIC_GUIDANCE["general_legal"])

    rights    = guidance_raw.get("rights",    [])
    steps     = guidance_raw.get("steps",     [])
    documents = guidance_raw.get("documents", [])

    if len(rights)    < 3:
        rights    = static["rights"]
    if len(steps)     < 3:
        steps     = static["steps"]
    if len(documents) < 3:
        documents = static["documents"]

    result = {
        "rights":             rights,
        "steps":              steps,
        "documents":          documents,
        "urgency":            guidance_raw.get("urgency",            "medium"),
        "urgency_reason":     guidance_raw.get("urgency_reason",     ""),
        "legal_domain":       INTENT_DOMAIN_MAP.get(intent, "General Legal Guidance"),
        "time_limit_warning": guidance_raw.get("time_limit_warning", "")
    }

    logger.info(
        f"[Guidance] Processed — domain: {result['legal_domain']} | "
        f"urgency: {result['urgency']} | "
        f"rights: {len(result['rights'])} | "
        f"steps: {len(result['steps'])} | "
        f"docs: {len(result['documents'])}"
    )
    return result


# ─────────────────────────────────────────────
# FORMAT FOR API RESPONSE
# ─────────────────────────────────────────────

def format_guidance_for_response(guidance: Dict) -> Dict:
    """
    Convert flat guidance dict into numbered API-ready structure.
    """
    urgency_emoji = {
        "low":    "🟢",
        "medium": "🟡",
        "high":   "🔴"
    }.get(guidance.get("urgency", "medium"), "🟡")

    return {
        "legal_domain":       guidance.get("legal_domain", ""),
        "urgency":            guidance.get("urgency", "medium"),
        "urgency_display":    f"{urgency_emoji} {guidance.get('urgency', 'medium').upper()}",
        "urgency_reason":     guidance.get("urgency_reason", ""),
        "time_limit_warning": guidance.get("time_limit_warning", ""),
        "rights": [
            {"id": i + 1, "description": r}
            for i, r in enumerate(guidance.get("rights", []))
        ],
        "steps": [
            {"step": i + 1, "action": s}
            for i, s in enumerate(guidance.get("steps", []))
        ],
        "documents": [
            {"id": i + 1, "document": d}
            for i, d in enumerate(guidance.get("documents", []))
        ]
    }