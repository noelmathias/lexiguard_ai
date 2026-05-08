
'EOF'
import sys
sys.path.insert(0, ".")
from core.agents import _parse_answer_text, _run_analysis

# Test parser with well-formed text
sample = """
ANALYSIS:
A landlord who locks out a tenant without notice is typically engaging
in an illegal self-help eviction in most jurisdictions.

RIGHTS:
Right to remain in the property
Right to seek re-entry through courts
Right to claim damages for illegal lockout

STEPS:
1. Document the lockout with photos
2. Send written demand to landlord
3. Consult a tenant rights lawyer

DOCUMENTS:
Signed lease agreement
Written communications with landlord

URGENCY: high
URGENCY_REASON: Illegal lockout requires immediate action.

CAUTION:
Please consult a qualified lawyer for advice specific to your situation.
"""

result = _parse_answer_text(sample)
assert result["urgency"]       == "high",             f"Got: {result['urgency']}"
assert len(result["rights"])   == 3,                  f"Got: {result['rights']}"
assert len(result["steps"])    == 3,                  f"Got: {result['steps']}"
assert len(result["documents"])== 2,                  f"Got: {result['documents']}"
assert "landlord"              in result["analysis"],  f"Got: {result['analysis']}"
print("✅ Answer parser OK")

# Test parser with missing sections (graceful degradation)
partial = "ANALYSIS:\nThe tenant has rights in this situation."
result2 = _parse_answer_text(partial)
assert result2["analysis"]             != ""
assert result2["urgency"]              in ("low","medium","high")
assert len(result2["rights"])          > 0
print("✅ Partial text parser OK")

# Test parser with no sections at all (worst case)
result3 = _parse_answer_text("The tenant may have rights here.")
assert result3["analysis"] != ""
assert result3["urgency"]  in ("low","medium","high")
print("✅ No-section fallback OK")

print("\n✅ All checks passed")
