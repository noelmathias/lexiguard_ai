// Document generation
import { useState, useEffect } from 'react'
import { FileEdit, Copy, Check } from 'lucide-react'
import { generateDocument, getDocumentTypes } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'

function PlaceholderTag({ label }) {
  return (
    <span style={{
      display: 'inline-block',
      background: '#4f8ef722',
      color: 'var(--accent)',
      border: '1px solid #4f8ef744',
      borderRadius: 6,
      padding: '1px 8px',
      fontSize: 11,
      fontWeight: 700,
      margin: '2px 3px',
      fontFamily: 'monospace'
    }}>[{label}]</span>
  )
}

function Section({ section }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 11, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '0.08em',
        color: 'var(--accent)', marginBottom: 6
      }}>
        {section.heading}
      </div>
      <div style={{
        fontSize: 13, color: 'var(--text)', lineHeight: 1.75,
        whiteSpace: 'pre-wrap', paddingLeft: 12,
        borderLeft: '2px solid var(--border)'
      }}>
        {section.content || '—'}
      </div>
    </div>
  )
}

export default function DocumentGen() {
  const [docTypes, setDocTypes]   = useState([])
  const [docType, setDocType]     = useState('legal_notice')
  const [situation, setSituation] = useState('')
  const [useLlm, setUseLlm]       = useState(true)
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState('')
  const [copied, setCopied]       = useState(false)
  const [view, setView]           = useState('sections')   // 'sections' | 'raw'

  useEffect(() => {
    getDocumentTypes()
      .then(r => setDocTypes(r.data.document_types))
      .catch(() => {})
  }, [])

  async function generate() {
    if (!situation.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { data } = await generateDocument(docType, situation, useLlm)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Generation failed.')
    } finally {
      setLoading(false)
    }
  }

  function copyText() {
    navigator.clipboard.writeText(result?.document?.full_text || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const selectedType = docTypes.find(t => t.type === docType)

  return (
    <div style={{ padding: 24, maxWidth: 820, margin: '0 auto', width: '100%' }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
        Generate Legal Document
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Describe your situation and get a professional legal document draft
      </p>

      {/* Config */}
      <div className="card" style={{ marginBottom: 20 }}>

        {/* Document type */}
        <div style={{ marginBottom: 16 }}>
          <div className="section-title">Document Type</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {docTypes.map(t => (
              <button
                key={t.type}
                className={`btn ${docType === t.type ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: 13, padding: '8px 16px' }}
                onClick={() => setDocType(t.type)}
              >
                {t.label}
              </button>
            ))}
          </div>
          {selectedType && (
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>
              {selectedType.description}
            </p>
          )}
        </div>

        <div className="divider" />

        {/* Situation */}
        <div style={{ marginBottom: 16 }}>
          <div className="section-title">Describe Your Situation</div>
          <textarea
            className="textarea"
            placeholder={
              docType === 'fir_draft'
                ? 'Describe the incident: what happened, when, where, who was involved, any witnesses or evidence...'
                : docType === 'complaint_letter'
                ? 'Describe the problem: what was purchased or agreed, what went wrong, what response you received...'
                : 'Describe the dispute: who owes what, what happened, what remedy you are seeking...'
            }
            value={situation}
            onChange={e => setSituation(e.target.value)}
            style={{ minHeight: 130 }}
          />
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
            Include names, dates, amounts, and locations for best results.
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 13, color: 'var(--muted)', cursor: 'pointer'
          }}>
            <input type="checkbox" checked={useLlm}
              onChange={e => setUseLlm(e.target.checked)} />
            AI-enhanced generation
          </label>
          <button
            className="btn btn-primary"
            style={{ marginLeft: 'auto' }}
            onClick={generate}
            disabled={!situation.trim() || loading}
          >
            <FileEdit size={15} />
            {loading ? 'Generating...' : 'Generate Document'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 12, color: 'var(--danger)', fontSize: 13 }}>
            ⚠️ {error}
          </div>
        )}
      </div>

      {loading && <LoadingSpinner label="Drafting your document..." />}

      {result && (
        <div className="card">
          {/* Doc header */}
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap', gap: 12
          }}>
            <div>
              <h2 style={{ fontSize: 17, fontWeight: 800 }}>
                {result.document?.title}
              </h2>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                {result.generated_date} · {result.word_count} words ·{' '}
                <span style={{
                  color: result.generation_mode === 'llm'
                    ? 'var(--accent)' : 'var(--muted)'
                }}>
                  {result.generation_mode === 'llm' ? 'AI generated' : 'Template'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={`btn btn-secondary`}
                style={{ fontSize: 12, padding: '7px 14px' }}
                onClick={() => setView(v => v === 'sections' ? 'raw' : 'sections')}
              >
                {view === 'sections' ? 'Raw Text' : 'Sections'}
              </button>
              <button
                className="btn btn-secondary"
                style={{ fontSize: 12, padding: '7px 14px' }}
                onClick={copyText}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Quality warnings */}
          {result.quality && !result.quality.passed && (
            <div style={{
              background: '#78350f22', border: '1px solid #f59e0b44',
              borderRadius: 'var(--radius)', padding: '10px 14px',
              fontSize: 13, color: 'var(--warn)', marginBottom: 16
            }}>
              ⚠️ {result.quality.issues?.join(' · ')}
            </div>
          )}

          {/* Placeholders */}
          {result.document?.placeholders?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div className="section-title">Fields to Fill In</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {result.document.placeholders.map((p, i) => (
                  <PlaceholderTag key={i} label={p} />
                ))}
              </div>
            </div>
          )}

          <div className="divider" />

          {/* Document content */}
          {view === 'sections'
            ? result.document?.sections?.map((s, i) => (
                <Section key={i} section={s} />
              ))
            : (
              <pre style={{
                whiteSpace: 'pre-wrap', fontSize: 12,
                fontFamily: 'monospace', lineHeight: 1.8,
                color: 'var(--text)', padding: '16px',
                background: 'var(--surface2)', borderRadius: 'var(--radius)'
              }}>
                {result.document?.full_text}
              </pre>
            )
          }

          {/* Disclaimer */}
          <div style={{
            marginTop: 20, padding: '12px 16px',
            background: 'var(--surface2)', borderRadius: 'var(--radius)',
            fontSize: 12, color: 'var(--muted)',
            borderLeft: '3px solid var(--border)'
          }}>
            ⚠️ {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  )
}