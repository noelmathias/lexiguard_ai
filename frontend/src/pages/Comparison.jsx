// A vs B comparison
import { useState, useRef } from 'react'
import { Upload, GitCompare } from 'lucide-react'
import { compareContracts } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'

const SEVERITY_COLOUR = {
  high:   'var(--danger)',
  medium: 'var(--warn)',
  low:    'var(--safe)'
}

const RISK_COLOUR = {
  safe:   'var(--safe)',
  risky:  'var(--warn)',
  unfair: 'var(--danger)'
}

function FileDropZone({ label, file, onFile }) {
  const ref = useRef(null)
  return (
    <div
      style={{
        border: `2px dashed ${file ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius)', padding: 24,
        textAlign: 'center', cursor: 'pointer',
        background: file ? '#4f8ef711' : 'transparent',
        flex: 1, minWidth: 200
      }}
      onClick={() => ref.current?.click()}
      onDragOver={e => e.preventDefault()}
      onDrop={e => { e.preventDefault(); onFile(e.dataTransfer.files[0]) }}
    >
      <input ref={ref} type="file" hidden accept=".pdf,.txt"
        onChange={e => onFile(e.target.files[0])} />
      <Upload size={24} color={file ? 'var(--accent)' : 'var(--muted)'}
        style={{ marginBottom: 8 }} />
      <div style={{ fontWeight: 600, fontSize: 13 }}>{label}</div>
      {file
        ? <div style={{ fontSize: 12, color: 'var(--accent)', marginTop: 4 }}>
            {file.name}
          </div>
        : <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
            PDF or TXT
          </div>
      }
    </div>
  )
}

function ComparisonRow({ row }) {
  const sevColour = SEVERITY_COLOUR[row.severity] || 'var(--muted)'
  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td style={{ padding: '12px 14px', fontSize: 13, fontWeight: 600 }}>
        {row.clause_title}
      </td>
      <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--muted)',
        maxWidth: 180 }}>
        {row.text_a || '—'}
      </td>
      <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--muted)',
        maxWidth: 180 }}>
        {row.text_b || '—'}
      </td>
      <td style={{ padding: '12px 14px' }}>
        <span style={{
          fontSize: 12, fontWeight: 700,
          color: RISK_COLOUR[row.risk_label_a] || 'var(--text)'
        }}>{row.risk_display_a}</span>
      </td>
      <td style={{ padding: '12px 14px' }}>
        <span style={{
          fontSize: 12, fontWeight: 700,
          color: RISK_COLOUR[row.risk_label_b] || 'var(--text)'
        }}>{row.risk_display_b}</span>
      </td>
      <td style={{ padding: '12px 14px', fontSize: 12, color: sevColour,
        fontWeight: 700 }}>
        {row.severity_display}
      </td>
      <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--muted)',
        maxWidth: 200 }}>
        {row.difference}
      </td>
    </tr>
  )
}

export default function Comparison() {
  const [fileA, setFileA]       = useState(null)
  const [fileB, setFileB]       = useState(null)
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState('')
  const [useLlm, setUseLlm]     = useState(true)

  async function compare() {
    if (!fileA || !fileB) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { data } = await compareContracts(fileA, fileB, useLlm)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Comparison failed.')
    } finally {
      setLoading(false)
    }
  }

  const recColour = {
    prefer_a:       'var(--safe)',
    prefer_b:       'var(--safe)',
    negotiate_both: 'var(--warn)',
    reject_both:    'var(--danger)'
  }

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto', width: '100%' }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
        Compare Contracts
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Upload two contracts to compare clause-by-clause with risk analysis
      </p>

      {/* Upload */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
          <FileDropZone label="Document A" file={fileA} onFile={setFileA} />
          <div style={{ display: 'flex', alignItems: 'center', color: 'var(--muted)' }}>
            <GitCompare size={20} />
          </div>
          <FileDropZone label="Document B" file={fileB} onFile={setFileB} />
        </div>

        <div style={{
          display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap'
        }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 13, color: 'var(--muted)', cursor: 'pointer'
          }}>
            <input type="checkbox" checked={useLlm}
              onChange={e => setUseLlm(e.target.checked)} />
            Use AI Comparison
          </label>
          <button
            className="btn btn-primary"
            style={{ marginLeft: 'auto' }}
            onClick={compare}
            disabled={!fileA || !fileB || loading}
          >
            Compare Documents
          </button>
        </div>
        {error && (
          <div style={{ marginTop: 12, color: 'var(--danger)', fontSize: 13 }}>
            ⚠️ {error}
          </div>
        )}
      </div>

      {loading && <LoadingSpinner label="Comparing contracts..." />}

      {result && (
        <>
          {/* Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
            marginBottom: 16 }}>
            {[
              { name: result.document_a_name, score: result.overall_risk_score_a,
                display: result.overall_risk_display_a },
              { name: result.document_b_name, score: result.overall_risk_score_b,
                display: result.overall_risk_display_b }
            ].map((doc, i) => (
              <div key={i} className="card">
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 6,
                  fontWeight: 700, textTransform: 'uppercase' }}>
                  {i === 0 ? 'Document A' : 'Document B'}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
                  {doc.name}
                </div>
                <div style={{
                  fontSize: 28, fontWeight: 800,
                  color: doc.score >= 70 ? 'var(--danger)' :
                         doc.score >= 40 ? 'var(--warn)' : 'var(--safe)'
                }}>
                  {doc.score}/100
                </div>
                <div style={{ fontSize: 12, fontWeight: 700,
                  color: doc.score >= 70 ? 'var(--danger)' :
                         doc.score >= 40 ? 'var(--warn)' : 'var(--safe)'
                }}>
                  {doc.display}
                </div>
              </div>
            ))}
          </div>

          {/* Recommendation */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center',
              flexWrap: 'wrap' }}>
              <div>
                <div className="section-title">Recommendation</div>
                <div style={{
                  fontSize: 18, fontWeight: 800,
                  color: recColour[result.recommendation] || 'var(--text)'
                }}>
                  {result.recommendation_display}
                </div>
                <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>
                  {result.recommendation_reason}
                </div>
              </div>
              <div style={{ marginLeft: 'auto' }}>
                <div className="section-title">Riskier Document</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--danger)' }}>
                  {result.riskier_display}
                </div>
              </div>
            </div>

            {result.key_differences?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="section-title">Key Differences</div>
                {result.key_differences.map((d, i) => (
                  <div key={i} style={{
                    fontSize: 13, padding: '5px 0',
                    borderBottom: '1px solid var(--border)',
                    color: 'var(--muted)', display: 'flex', gap: 8
                  }}>
                    <span>•</span><span>{d}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Table */}
          <div className="card" style={{ overflowX: 'auto' }}>
            <div className="section-title" style={{ marginBottom: 14 }}>
              Clause-by-Clause Comparison ({result.total_clauses_compared} clauses)
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Clause', 'Doc A Text', 'Doc B Text',
                    'Risk A', 'Risk B', 'Severity', 'Difference'
                  ].map(h => (
                    <th key={h} style={{
                      padding: '10px 14px', textAlign: 'left',
                      fontSize: 11, color: 'var(--muted)',
                      fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.06em'
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.comparison_table.map((row, i) => (
                  <ComparisonRow key={i} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}