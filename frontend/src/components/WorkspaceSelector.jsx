import { useState } from 'react'
import { Plus, ChevronDown, Briefcase, X } from 'lucide-react'
import { useWorkspace } from '../context/WorkspaceContext'

function CreateModal({ onClose, onCreated }) {
  const { addWorkspace } = useWorkspace()
  const [name, setName]  = useState('')
  const [desc, setDesc]  = useState('')
  const [busy, setBusy]  = useState(false)

  async function submit() {
    if (!name.trim()) return
    setBusy(true)
    try {
      const ws = await addWorkspace(name.trim(), desc.trim())
      onCreated(ws)
      onClose()
    } catch {
      alert('Failed to create workspace.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: '#00000088', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: 380, padding: 28 }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: 20
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 700 }}>New Workspace</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none',
              color: 'var(--muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div className="section-title">Workspace Name</div>
          <input
            className="input"
            placeholder="e.g. Tenant Dispute 2025"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            autoFocus
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <div className="section-title">Description (optional)</div>
          <input
            className="input"
            placeholder="Brief description of this matter"
            value={desc}
            onChange={e => setDesc(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={!name.trim() || busy}
          >
            {busy ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function WorkspaceSelector() {
  const { workspaces, activeWs, selectWorkspace } = useWorkspace()
  const [open,      setOpen]      = useState(false)
  const [showModal, setShowModal] = useState(false)

  return (
    <>
      {showModal && (
        <CreateModal
          onClose={()   => setShowModal(false)}
          onCreated={ws => selectWorkspace(ws)}
        />
      )}

      <div style={{ padding: '12px 10px', borderBottom: '1px solid var(--border)' }}>
        <div className="section-title" style={{ padding: '0 6px', marginBottom: 6 }}>
          Workspace
        </div>

        {/* Selector trigger */}
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            width: '100%', background: 'var(--surface2)',
            border: '1px solid var(--border)', borderRadius: 8,
            padding: '8px 10px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8,
            color: 'var(--text)', fontSize: 13
          }}
        >
          <Briefcase size={14} color="var(--accent)" style={{ flexShrink: 0 }} />
          <span style={{
            flex: 1, textAlign: 'left', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            color: activeWs ? 'var(--text)' : 'var(--muted)'
          }}>
            {activeWs ? activeWs.name : 'Global (no workspace)'}
          </span>
          <ChevronDown size={13} color="var(--muted)" />
        </button>

        {/* Dropdown */}
        {open && (
          <div style={{
            marginTop: 4,
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            borderRadius: 8, overflow: 'hidden',
            boxShadow: '0 8px 24px #00000044'
          }}>
            {/* Global option */}
            <div
              onClick={() => { selectWorkspace(null); setOpen(false) }}
              style={{
                padding: '9px 12px', cursor: 'pointer', fontSize: 13,
                color: !activeWs ? 'var(--accent)' : 'var(--muted)',
                background: !activeWs ? '#4f8ef711' : 'transparent',
                borderBottom: '1px solid var(--border)'
              }}
            >
              🌐 Global (no workspace)
            </div>

            {/* Workspace list */}
            <div style={{ maxHeight: 180, overflowY: 'auto' }}>
              {workspaces.map(ws => (
                <div
                  key={ws.id}
                  onClick={() => { selectWorkspace(ws); setOpen(false) }}
                  style={{
                    padding: '9px 12px', cursor: 'pointer', fontSize: 13,
                    color: activeWs?.id === ws.id ? 'var(--accent)' : 'var(--text)',
                    background: activeWs?.id === ws.id ? '#4f8ef711' : 'transparent',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', gap: 8
                  }}
                >
                  <Briefcase size={13} />
                  <span style={{
                    flex: 1, overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                  }}>{ws.name}</span>
                </div>
              ))}
              {workspaces.length === 0 && (
                <div style={{ padding: '10px 12px', fontSize: 12,
                  color: 'var(--muted)', textAlign: 'center' }}>
                  No workspaces yet
                </div>
              )}
            </div>

            {/* New workspace button */}
            <div
              onClick={() => { setOpen(false); setShowModal(true) }}
              style={{
                padding: '9px 12px', cursor: 'pointer', fontSize: 13,
                color: 'var(--accent)', display: 'flex',
                alignItems: 'center', gap: 8,
                borderTop: '1px solid var(--border)'
              }}
            >
              <Plus size={14} /> New Workspace
            </div>
          </div>
        )}
      </div>
    </>
  )
}