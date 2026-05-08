import {
  createContext, useContext, useState,
  useEffect, useCallback
} from 'react'

// Self-contained UUID — no external dependency
const uuidv4 = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })

const WorkspaceCtx = createContext(null)

function loadFromStorage() {
  try {
    return JSON.parse(localStorage.getItem('lex_workspaces') || '[]')
  } catch {
    return []
  }
}

function saveToStorage(workspaces) {
  try {
    localStorage.setItem('lex_workspaces', JSON.stringify(workspaces))
  } catch {
    // storage quota exceeded — fail silently
  }
}

export function WorkspaceProvider({ children }) {
  const [workspaces,    setWorkspaces]    = useState(loadFromStorage)
  const [activeWs,      setActiveWs]      = useState(null)
  const [activeSession, setActiveSession] = useState(null)

  // Restore last active workspace on mount
  useEffect(() => {
    try {
      const savedId = localStorage.getItem('lex_active_ws')
      if (savedId) {
        const ws = loadFromStorage().find(w => w.id === savedId)
        if (ws) setActiveWs(ws)
      }
    } catch {
      // ignore storage errors
    }
  }, [])

  const selectWorkspace = useCallback((ws) => {
    setActiveWs(ws)
    setActiveSession(null)
    try {
      if (ws) {
        localStorage.setItem('lex_active_ws', ws.id)
      } else {
        localStorage.removeItem('lex_active_ws')
      }
    } catch {
      // ignore
    }
  }, [])

  const addWorkspace = useCallback((name, description = '') => {
    const ws = {
      id:          uuidv4(),
      name:        name.trim(),
      description: description.trim(),
      created_at:  new Date().toISOString()
    }
    setWorkspaces(prev => {
      const updated = [ws, ...prev]
      saveToStorage(updated)
      return updated
    })
    return ws
  }, [])

  const deleteWorkspace = useCallback((id) => {
    setWorkspaces(prev => {
      const updated = prev.filter(w => w.id !== id)
      saveToStorage(updated)
      return updated
    })
    setActiveWs(prev => {
      if (prev?.id === id) {
        try { localStorage.removeItem('lex_active_ws') } catch {}
        return null
      }
      return prev
    })
    setActiveSession(null)
  }, [])

  return (
    <WorkspaceCtx.Provider value={{
      workspaces,
      activeWs,
      activeSession,
      selectWorkspace,
      addWorkspace,
      deleteWorkspace,
      setActiveSession,
    }}>
      {children}
    </WorkspaceCtx.Provider>
  )
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceCtx)
  if (!ctx) throw new Error(
    'useWorkspace() called outside <WorkspaceProvider>. ' +
    'Wrap your app in <WorkspaceProvider> in main.jsx.'
  )
  return ctx
}