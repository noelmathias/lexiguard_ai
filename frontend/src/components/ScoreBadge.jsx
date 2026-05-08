// Risk + confidence badges
export function RiskBadge({ score, display }) {
  const colour =
    score >= 70 ? 'var(--danger)' :
    score >= 40 ? 'var(--warn)'   :
    'var(--safe)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      background: 'var(--surface2)',
      border: `1px solid ${colour}44`,
      borderRadius: 'var(--radius)',
      padding: '12px 16px'
    }}>
      <div style={{ fontSize: 24 }}>
        {score >= 70 ? '🔴' : score >= 40 ? '🟡' : '🟢'}
      </div>
      <div>
        <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.06em' }}>Risk Level</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: colour }}>
          {display || `${score}/100`}
        </div>
      </div>
      <div style={{
        marginLeft: 'auto', fontSize: 22, fontWeight: 800, color: colour
      }}>{score}</div>
    </div>
  )
}

export function ConfidenceBadge({ score, display }) {
  const colour =
    score >= 70 ? 'var(--safe)'  :
    score >= 40 ? 'var(--warn)'  :
    'var(--danger)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      background: 'var(--surface2)',
      border: `1px solid ${colour}44`,
      borderRadius: 'var(--radius)',
      padding: '12px 16px'
    }}>
      <div style={{ fontSize: 24 }}>
        {score >= 70 ? '✅' : score >= 40 ? '⚠️' : '❌'}
      </div>
      <div>
        <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.06em' }}>Confidence</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: colour }}>
          {display || `${score}/100`}
        </div>
      </div>
      <div style={{
        marginLeft: 'auto', fontSize: 22, fontWeight: 800, color: colour
      }}>{score}</div>
    </div>
  )
}

export function ScoreBar({ label, value, max = 100, colour }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between',
        fontSize: 12, marginBottom: 4, color: 'var(--muted)' }}>
        <span>{label}</span><span>{value}/{max}</span>
      </div>
      <div style={{ background: 'var(--surface2)', borderRadius: 4,
        height: 6, overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: colour || 'var(--accent)',
          borderRadius: 4,
          transition: 'width 0.6s ease'
        }} />
      </div>
    </div>
  )
}