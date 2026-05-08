// Flags + warnings
export default function GuardrailBanner({ guardrails }) {
  if (!guardrails) return null

  const { blocked, block_reason, warnings = [],
          flags = [], hallucination_risk, was_modified } = guardrails

  if (!blocked && !warnings.length && !flags.length && !was_modified) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>

      {/* Blocked */}
      {blocked && (
        <div style={{
          background: '#7f1d1d22', border: '1px solid var(--danger)',
          borderRadius: 'var(--radius)', padding: '12px 16px',
          color: 'var(--danger)', fontSize: 13
        }}>
          🚫 <strong>Query Blocked:</strong> {block_reason}
        </div>
      )}

      {/* Hallucination risk */}
      {hallucination_risk === 'high' && (
        <div style={{
          background: '#78350f22', border: '1px solid var(--warn)',
          borderRadius: 'var(--radius)', padding: '12px 16px',
          color: 'var(--warn)', fontSize: 13
        }}>
          ⚠️ <strong>High Hallucination Risk Detected.</strong> Verify all
          specific legal references with a qualified lawyer before acting.
        </div>
      )}

      {/* Warnings */}
      {warnings.map((w, i) => (
        <div key={i} style={{
          background: 'var(--surface2)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: '10px 14px',
          fontSize: 13, color: 'var(--muted)'
        }}>
          ℹ️ {w}
        </div>
      ))}

      {/* Modified notice */}
      {was_modified && !blocked && (
        <div style={{ fontSize: 11, color: 'var(--muted)', padding: '4px 2px' }}>
          ✏️ Response was reviewed and adjusted by the guardrails system.
        </div>
      )}
    </div>
  )
}