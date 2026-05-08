// PDF upload + analysis
import { useState, useRef } from 'react'
import { Upload, FileText, AlertTriangle } from 'lucide-react'
import { analyzeContract } from '../api/client'
import { ScoreBar } from '../components/ScoreBadge'
import LoadingSpinner from '../components/LoadingSpinner'

const LABEL_STYLE = {
  safe:   { bg: '#14532d22', color: '#22c55e', border: '#22c55e44' },
  risky:  { bg: '#78350f22', color: '#f59e0b', border: '#f59e0b44' },
  unfair: { bg: '#7f1d1d22', color: '#ef4444', border: '#ef444444' }
}

function ClauseCard({ clause }) {
  const style  = LABEL_STYLE[clause.risk_label] || LABEL_STYLE.risky
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      border: `1px solid ${style.border}`,
      borderRadius: 'var(--radius)',
      background: style.bg,
      marginBottom: 10, overflow: 'hidden'
    }}>
      <div
        style={{
          padding: '12px 16px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 12
        }}
        onClick={() => setOpen(o => !o)}
      >
        <span style={{
          fontSize: 12, fontWeight: 700, color: style.color,
          background: `${style.color}22`, padding: '2px 8px',
          borderRadius: 12, whiteSpace: 'nowrap'
        }}>{clause.risk_display}</span>
        <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{clause.title}</span>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>
          Score: {clause.risk_score} {open ? '▲' : '▼'}
        </span>
      </div>
      {open && (
        <div style={{ padding: '0 16px 14px', fontSize: 13 }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 6,
            padding: '10px 12px', marginBottom: 10,
            fontFamily: 'monospace', fontSize: 12,
            color: 'var(--muted)', lineHeight: 1.6
          }}>{clause.text}</div>
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>
            💡 {clause.reason}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ContractAnalysis() {
  const [file, setFile]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState('')
  const [useLlm, setUseLlm]     = useState(true)
  const [activeTab, setTab]     = useState('all')
  const fileRef                 = useRef(null)

  async function analyse() {
    if (!file) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { data } = await analyzeContract(file, useLlm)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const recColour = {
    sign:      'var(--safe)',
    negotiate: 'var(--warn)',
    reject:    'var(--danger)'
  }

  const displayClauses = result?.clauses?.filter(c =>
    activeTab === 'all' ? true : c.risk_label === activeTab
  ) || []

  return (
    <div style={{ padding: 24, maxWidth: 860, margin: '0 auto', width: '100%' }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
        Contract Analysis
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Upload a contract PDF or TXT to extract clauses and identify risk
      </p>

      {/* Upload card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div
          style={{
            border: '2px dashed var(--border)',
            borderRadius: 'var(--radius)', padding: '32px',
            textAlign: 'center', cursor: 'pointer',
            background: file ? '#4f8ef711' : 'transparent',
            transition: 'all 0.15s',
            borderColor: file ? 'var(--accent)' : 'var(--border)'
          }}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]) }}
        >
          <input
            ref={fileRef} type="file" hidden
            accept=".pdf,.txt"
            onChange={e => setFile(e.target.files[0])}
          />
          {file ? (
            <>
              <FileText size={32} color="var(--accent)" style={{ marginBottom: 8 }} />
              <div style={{ fontWeight: 700 }}>{file.name}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                {(file.size / 1024).toFixed(1)} KB — click to change
              </div>
            </>
          ) : (
            <>
              <Upload size={32} color="var(--muted)" style={{ marginBottom: 8 }} />
              <div style={{ fontWeight: 600 }}>Drop PDF or TXT here</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>or click to browse</div>
            </>
          )}
        </div>

        <div style={{
          display: 'flex', gap: 12, marginTop: 16,
          alignItems: 'center', flexWrap: 'wrap'
        }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 13, color: 'var(--muted)', cursor: 'pointer'
          }}>
            <input
              type="checkbox" checked={useLlm}
              onChange={e => setUseLlm(e.target.checked)}
            />
            Use AI Analysis (recommended)
          </label>
          <button
            className="btn btn-primary"
            style={{ marginLeft: 'auto' }}
            onClick={analyse}
            disabled={!file || loading}
          >
            {loading ? 'Analysing...' : 'Analyse Contract'}
          </button>
        </div>

        {error && (
          <div style={{
            marginTop: 12, color: 'var(--danger)',
            fontSize: 13, display: 'flex', gap: 8
          }}>
            <AlertTriangle size={16} /> {error}
          </div>
        )}
      </div>

      {loading && <LoadingSpinner label="Extracting and analysing clauses..." />}

      {/* Results */}
      {result && (
        <>
          {/* Overview */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 16 }}>
              <div style={{ flex: 1, minWidth: 180 }}>
                <ScoreBar
                  label="Overall Risk"
                  value={result.overall_risk_score}
                  colour={
                    result.overall_risk_score >= 70 ? 'var(--danger)' :
                    result.overall_risk_score >= 40 ? 'var(--warn)' : 'var(--safe)'
                  }
                />
              </div>
              <div style={{
                display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap'
              }}>
                <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700,
                  textTransform: 'uppercase', letterSpacing: '0.06em' }}>Verdict</span>
                <span style={{
                  fontWeight: 800, fontSize: 16,
                  color: recColour[result.recommendation] || 'var(--text)'
                }}>{result.recommendation_display}</span>
              </div>
            </div>

            <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
              {result.summary}
            </p>

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <div style={{
                background: '#7f1d1d22', border: '1px solid #ef444444',
                borderRadius: 8, padding: '10px 16px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--danger)' }}>
                  {result.unfair_count}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Unfair</div>
              </div>
              <div style={{
                background: '#78350f22', border: '1px solid #f59e0b44',
                borderRadius: 8, padding: '10px 16px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--warn)' }}>
                  {result.risky_count}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Risky</div>
              </div>
              <div style={{
                background: '#14532d22', border: '1px solid #22c55e44',
                borderRadius: 8, padding: '10px 16px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--safe)' }}>
                  {result.safe_count}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Safe</div>
              </div>
            </div>

            {/* Critical issues */}
            {result.critical_issues?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="section-title">Critical Issues</div>
                {result.critical_issues.map((issue, i) => (
                  <div key={i} style={{
                    fontSize: 13, padding: '6px 0',
                    borderBottom: '1px solid var(--border)',
                    color: 'var(--danger)', display: 'flex', gap: 8
                  }}>
                    <span>🚨</span><span>{issue}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Clause list */}
          <div className="card">
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              {['all', 'unfair', 'risky', 'safe'].map(tab => (
                <button
                  key={tab}
                  className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '6px 14px', fontSize: 12 }}
                  onClick={() => setTab(tab)}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === 'all'
                    ? ` (${result.clause_count})`
                    : ` (${result[`${tab}_count`] || 0})`
                  }
                </button>
              ))}
            </div>
            {displayClauses.map((c, i) => <ClauseCard key={i} clause={c} />)}
            {displayClauses.length === 0 && (
              <div style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center',
                padding: 20 }}>No clauses in this category.</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}