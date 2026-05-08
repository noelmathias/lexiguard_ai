// Rights, steps, documents
export default function GuidancePanel({ guidance }) {
  if (!guidance) return null

  const urgencyColour = {
    high:   'var(--danger)',
    medium: 'var(--warn)',
    low:    'var(--safe)'
  }[guidance.urgency] || 'var(--muted)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Domain + Urgency */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <span className="tag tag-info">{guidance.legal_domain}</span>
        <span className="tag" style={{
          background: `${urgencyColour}22`,
          color: urgencyColour,
          border: `1px solid ${urgencyColour}44`
        }}>
          {guidance.urgency_display}
        </span>
      </div>

      {guidance.urgency_reason && (
        <p style={{ fontSize: 13, color: 'var(--muted)' }}>
          {guidance.urgency_reason}
        </p>
      )}

      {guidance.time_limit_warning && (
        <div style={{
          background: '#78350f22', border: '1px solid #f59e0b44',
          borderRadius: 'var(--radius)', padding: '10px 14px',
          fontSize: 13, color: 'var(--warn)'
        }}>
          ⏰ {guidance.time_limit_warning}
        </div>
      )}

      {/* Rights */}
      {guidance.rights?.length > 0 && (
        <div>
          <div className="section-title">Your Rights</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {guidance.rights.map((r, i) => (
              <div key={i} style={{
                display: 'flex', gap: 10, alignItems: 'flex-start',
                fontSize: 13, padding: '6px 0',
                borderBottom: '1px solid var(--border)'
              }}>
                <span style={{ color: 'var(--safe)', fontSize: 15, flexShrink: 0 }}>✓</span>
                <span>{r.description || r}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Steps */}
      {guidance.steps?.length > 0 && (
        <div>
          <div className="section-title">Recommended Steps</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {guidance.steps.map((s, i) => (
              <div key={i} style={{
                display: 'flex', gap: 12, alignItems: 'flex-start', fontSize: 13
              }}>
                <div style={{
                  width: 22, height: 22, borderRadius: '50%',
                  background: 'var(--accent)', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, flexShrink: 0, marginTop: 1
                }}>{i + 1}</div>
                <span>{s.action || s}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documents */}
      {guidance.documents?.length > 0 && (
        <div>
          <div className="section-title">Documents You Need</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {guidance.documents.map((d, i) => (
              <div key={i} style={{
                fontSize: 13, display: 'flex', gap: 8, alignItems: 'flex-start'
              }}>
                <span style={{ color: 'var(--accent)', flexShrink: 0 }}>📄</span>
                <span>{d.document || d}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}