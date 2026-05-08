import { useState, useEffect, useRef } from 'react'
import { Upload, Trash2, FileText, MessageSquare,
         FileEdit, RefreshCw, AlertTriangle } from 'lucide-react'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  getWorkspaceDocs, uploadWorkspaceDoc, deleteWorkspaceDoc,
  getChatSessions, deleteChatSession,
  getGeneratedDocs, deleteWorkspace
} from '../api/client'
import { useNavigate } from 'react-router-dom'
import LoadingSpinner from '../components/LoadingSpinner'

function DocRow({ doc, onDelete }) {
  const [busy, setBusy] = useState(false)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 0', borderBottom: '1px solid var(--border)',
      fontSize: 13
    }}>
      <FileText size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontWeight: 600, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap'
        }}>{doc.filename}</div>
        <div style={{ fontSize: 11, color: 'var(--muted)' }}>
          {doc.word_count} words · {doc.chunk_count} chunks ·{' '}
          {doc.indexed ? '✅ Indexed' : '⏳ Pending'}
        </div>
      </div>
      <button
        className="btn btn-secondary"
        style={{ padding: '5px 10px', fontSize: 12 }}
        disabled={busy}
        onClick={async () => {
          if (!confirm('Delete this document?')) return
          setBusy(true)
          await onDelete(doc.id)
          setBusy(false)
        }}
      >
        <Trash2 size={13} />
      </button>
    </div>
  )
}

function SessionRow({ session, wsId, onDelete }) {
  const navigate = useNavigate()
  const { setActiveSession } = useWorkspace()
  const [busy, setBusy] = useState(false)

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 0', borderBottom: '1px solid var(--border)',
      fontSize: 13
    }}>
      <MessageSquare size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontWeight: 600, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap'
        }}>{session.title}</div>
        <div style={{ fontSize: 11, color: 'var(--muted)' }}>
          {new Date(session.updated_at).toLocaleDateString()}
        </div>
      </div>
      <button
        className="btn btn-secondary"
        style={{ padding: '5px 10px', fontSize: 12 }}
        onClick={() => {
          setActiveSession(session.id)
          navigate('/')
        }}
      >
        Open
      </button>
      <button
        className="btn btn-secondary"
        style={{ padding: '5px 10px', fontSize: 12 }}
        disabled={busy}
        onClick={async () => {
          if (!confirm('Delete this session?')) return
          setBusy(true)
          await onDelete(session.id)
          setBusy(false)
        }}
      >
        <Trash2 size={13} />
      </button>
    </div>
  )
}

function GeneratedDocRow({ doc }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ borderBottom: '1px solid var(--border)' }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '10px 0', fontSize: 13, cursor: 'pointer'
        }}
        onClick={() => setOpen(o => !o)}
      >
        <FileEdit size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600 }}>{doc.title}</div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            {doc.doc_type.replace(/_/g, ' ')} ·{' '}
            {doc.word_count} words ·{' '}
            {new Date(doc.created_at).toLocaleDateString()}
          </div>
        </div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>
          {open ? '▲' : '▼'}
        </span>
      </div>
      {open && (
        <pre style={{
          whiteSpace: 'pre-wrap', fontSize: 12, fontFamily: 'monospace',
          lineHeight: 1.7, padding: '12px 16px', marginBottom: 12,
          background: 'var(--surface2)', borderRadius: 8,
          color: 'var(--text)', maxHeight: 300, overflowY: 'auto'
        }}>
          {doc.full_text}
        </pre>
      )}
    </div>
  )
}

export default function WorkspaceDashboard() {
  const { activeWs, selectWorkspace, refresh: refreshWs } = useWorkspace()
  const navigate    = useNavigate()
  const fileRef     = useRef(null)

  const [docs,      setDocs]      = useState([])
  const [sessions,  setSessions]  = useState([])
  const [generated, setGenerated] = useState([])
  const [loading,   setLoading]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const [tab,       setTab]       = useState('documents')
  const [error,     setError]     = useState('')

  const wsId = activeWs?.id

  async function loadAll() {
    if (!wsId) return
    setLoading(true)
    setError('')
    try {
      const [d, s, g] = await Promise.all([
        getWorkspaceDocs(wsId),
        getChatSessions(wsId),
        getGeneratedDocs(wsId),
      ])
      setDocs(d.data.documents      || [])
      setSessions(s.data.sessions   || [])
      setGenerated(g.data.documents || [])
    } catch {
      setError('Failed to load workspace data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [wsId])

  async function handleUpload(file) {
    if (!file || !wsId) return
    setUploading(true)
    setError('')
    try {
      await uploadWorkspaceDoc(wsId, file)
      await loadAll()
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  async function handleDeleteDoc(docId) {
    await deleteWorkspaceDoc(wsId, docId)
    await loadAll()
  }

  async function handleDeleteSession(sessId) {
    await deleteChatSession(wsId, sessId)
    await loadAll()
  }

  async function handleDeleteWorkspace() {
    if (!confirm(`Delete workspace "${activeWs.name}" and all its data? This cannot be undone.`))
      return
    await deleteWorkspace(wsId)
    selectWorkspace(null)
    await refreshWs()
    navigate('/')
  }

  if (!activeWs) {
    return (
      <div style={{
        padding: 40, textAlign: 'center', color: 'var(--muted)'
      }}>
        <Briefcase size={40} style={{ marginBottom: 16, opacity: 0.4 }} />
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
          No Workspace Selected
        </div>
        <div style={{ fontSize: 13, maxWidth: 320, margin: '0 auto' }}>
          Select a workspace from the sidebar to view its documents,
          chat history, and generated documents.
        </div>
      </div>
    )
  }

  const tabs = [
    { id: 'documents', label: `Documents (${docs.length})` },
    { id: 'sessions',  label: `Chat History (${sessions.length})` },
    { id: 'generated', label: `Generated (${generated.length})` },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 780, margin: '0 auto', width: '100%' }}>

      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800 }}>{activeWs.name}</h1>
          {activeWs.description && (
            <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 2 }}>
              {activeWs.description}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: '7px 14px' }}
            onClick={loadAll}
          >
            <RefreshCw size={13} /> Refresh
          </button>
          <button
            className="btn btn-danger"
            style={{ fontSize: 12, padding: '7px 14px' }}
            onClick={handleDeleteWorkspace}
          >
            <Trash2 size={13} /> Delete Workspace
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: '#7f1d1d22', border: '1px solid var(--danger)',
          borderRadius: 'var(--radius)', padding: '10px 14px',
          color: 'var(--danger)', fontSize: 13, marginBottom: 16,
          display: 'flex', gap: 8
        }}>
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {tabs.map(t => (
          <button
            key={t.id}
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: 13, padding: '8px 16px' }}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <LoadingSpinner label="Loading workspace..." />}

      {/* Documents tab */}
      {!loading && tab === 'documents' && (
        <div className="card">
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', marginBottom: 16
          }}>
            <div className="section-title" style={{ marginBottom: 0 }}>
              Uploaded Documents
            </div>
            <div>
              <input
                ref={fileRef} type="file" hidden
                accept=".pdf,.txt"
                onChange={e => handleUpload(e.target.files[0])}
              />
              <button
                className="btn btn-primary"
                style={{ fontSize: 12, padding: '7px 14px' }}
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
              >
                <Upload size={13} />
                {uploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </div>
          </div>

          {docs.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: 13,
              textAlign: 'center', padding: '30px 0' }}>
              No documents uploaded yet. Upload PDFs or TXT files to
              make them available in your workspace chat.
            </div>
          ) : (
            docs.map(doc => (
              <DocRow key={doc.id} doc={doc} onDelete={handleDeleteDoc} />
            ))
          )}
        </div>
      )}

      {/* Sessions tab */}
      {!loading && tab === 'sessions' && (
        <div className="card">
          <div className="section-title" style={{ marginBottom: 16 }}>
            Chat Sessions
          </div>
          {sessions.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: 13,
              textAlign: 'center', padding: '30px 0' }}>
              No chat sessions yet. Start a legal chat to create one.
            </div>
          ) : (
            sessions.map(s => (
              <SessionRow
                key={s.id} session={s} wsId={wsId}
                onDelete={handleDeleteSession}
              />
            ))
          )}
        </div>
      )}

      {/* Generated docs tab */}
      {!loading && tab === 'generated' && (
        <div className="card">
          <div className="section-title" style={{ marginBottom: 16 }}>
            Generated Documents
          </div>
          {generated.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: 13,
              textAlign: 'center', padding: '30px 0' }}>
              No documents generated yet. Use the Generate Document
              feature to create legal notices, complaint letters, or FIR drafts.
            </div>
          ) : (
            generated.map(d => (
              <GeneratedDocRow key={d.id} doc={d} />
            ))
          )}
        </div>
      )}
    </div>
  )
}