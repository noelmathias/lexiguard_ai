from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────
# GUIDANCE SCHEMAS
# ─────────────────────────────────────────────

class RightItem(BaseModel):
    id:          int
    description: str

class StepItem(BaseModel):
    step:   int
    action: str

class DocumentItem(BaseModel):
    id:       int
    document: str

class LegalGuidance(BaseModel):
    legal_domain:       str
    urgency:            str
    urgency_display:    str
    urgency_reason:     str
    time_limit_warning: str
    rights:             List[RightItem]
    steps:              List[StepItem]
    documents:          List[DocumentItem]


# ─────────────────────────────────────────────
# SCORING SCHEMAS
# ─────────────────────────────────────────────

class RiskDetail(BaseModel):
    score:     int
    label:     str
    display:   str
    colour:    str
    flags:     List[str]
    breakdown: Dict[str, Any]

class ConfidenceDetail(BaseModel):
    score:       int
    label:       str
    display:     str
    colour:      str
    explanation: str
    components:  Dict[str, float]

class ScoreResponse(BaseModel):
    risk:            RiskDetail
    confidence:      ConfidenceDetail
    confidence_note: str
    summary:         str


# ─────────────────────────────────────────────
# GUARDRAILS SCHEMAS
# ─────────────────────────────────────────────

class GuardrailsResponse(BaseModel):
    status:             str
    blocked:            bool
    block_reason:       str
    warnings:           List[str]
    flags:              List[str]
    flag_count:         int
    hallucination_risk: str
    was_modified:       bool
    patches_applied:    List[str]
    patch_count:        int


# ─────────────────────────────────────────────
# CONTRACT SCHEMAS
# ─────────────────────────────────────────────

class ContractClause(BaseModel):
    type:         str
    title:        str
    text:         str
    risk_label:   str
    risk_display: str
    risk_score:   int
    reason:       str
    page_hint:    str

class ContractAnalysisResponse(BaseModel):
    filename:               str
    word_count:             int
    analysis_mode:          str
    status:                 str
    clauses:                List[ContractClause]
    clause_count:           int
    unfair_count:           int
    risky_count:            int
    safe_count:             int
    overall_risk_score:     int
    overall_risk_label:     str
    overall_risk_display:   str
    summary:                str
    critical_issues:        List[str]
    positive_aspects:       List[str]
    recommendation:         str
    recommendation_display: str
    recommendation_reason:  str


# ─────────────────────────────────────────────
# COMPARISON SCHEMAS
# ─────────────────────────────────────────────

class ComparisonRow(BaseModel):
    row_number:       int
    clause_type:      str
    clause_title:     str
    text_a:           str
    text_b:           str
    risk_label_a:     str
    risk_display_a:   str
    risk_score_a:     int
    risk_label_b:     str
    risk_display_b:   str
    risk_score_b:     int
    difference:       str
    favours:          str
    favours_display:  str
    severity:         str
    severity_display: str

class ComparisonResponse(BaseModel):
    status:                 str
    analysis_mode:          str
    document_a_name:        str
    document_b_name:        str
    comparison_table:       List[ComparisonRow]
    total_clauses_compared: int
    high_severity_count:    int
    overall_risk_score_a:   int
    overall_risk_score_b:   int
    overall_risk_display_a: str
    overall_risk_display_b: str
    riskier_document:       str
    riskier_display:        str
    key_differences:        List[str]
    advantages_a:           List[str]
    advantages_b:           List[str]
    recommendation:         str
    recommendation_display: str
    recommendation_reason:  str


# ─────────────────────────────────────────────
# QUERY SCHEMAS
# ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[dict]] = []
    workspace_id: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "query": "My landlord locked me out without notice. What can I do?",
            "chat_history": []
        }
    }}

class QueryResponse(BaseModel):
    answer:     str
    confidence: float
    risk_score: Optional[float]            = None
    sources:    Optional[List[str]]        = []
    input_type: Optional[str]              = None
    intent:     Optional[str]              = None
    entities:   Optional[Dict[str, Any]]   = None
    guidance:   Optional[LegalGuidance]    = None
    scores:     Optional[ScoreResponse]    = None
    guardrails: Optional[GuardrailsResponse] = None

# ─────────────────────────────────────────────
# DOCUMENT GENERATION SCHEMAS
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# DOCUMENT GENERATION SCHEMAS
# ─────────────────────────────────────────────

class DocumentContent(BaseModel):
    type:         str
    title:        str
    content:      str
    placeholders: List[str]

class DocumentRequest(BaseModel):
    doc_type:  str
    situation: str
    user_info: Optional[Dict[str, Any]] = None
    context:   Optional[str]            = ""

class DocumentResponse(BaseModel):
    status:          str
    doc_type:        str
    generated_date:  str
    generation_mode: str
    word_count:      int
    disclaimer:      str
    document:        DocumentContent
# ─────────────────────────────────────────────
# HEALTH SCHEMA
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:  str
    version: str