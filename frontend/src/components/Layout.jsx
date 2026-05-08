import { NavLink, Outlet } from 'react-router-dom'
import {
  MessageSquare, FileText,
  GitCompare, FileEdit, Scale
} from 'lucide-react'
import WorkspaceSelector from './WorkspaceSelector'
import { useWorkspace }  from '../context/WorkspaceContext'

const navItems = [
  { to: '/',         icon: MessageSquare, label: 'Legal Chat' },
  { to: '/contract', icon: FileText,      label: 'Contract Analysis' },
  { to: '/compare',  icon: GitCompare,    label: 'Compare Contracts' },
  { to: '/generate', icon: FileEdit,      label: 'Generate Document' },
]

export default function Layout() {
  const { activeWs } = useWorkspace()

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* Sidebar */}
      <aside style={{
        width: 224,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflowY: 'auto'
      }}>

        {/* Logo */}
        <div style={{
          padding: '18px 18px 14px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 10,
          flexShrink: 0
        }}>
          <Scale size={22} color="var(--accent)" />
          <div>
            <div style={{ fontWeight: 800, fontSize: 15 }}>LexAI</div>
            <div style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Legal Intelligence
            </div>
          </div>
        </div>

        {/* Workspace selector — local state only, no backend calls */}
        <WorkspaceSelector />

        {/* Active workspace badge */}
        {activeWs && (
          <div style={{
            margin: '8px 10px 0',
            padding: '6px 10px',
            background: '#4f8ef711',
            border: '1px solid #4f8ef733',
            borderRadius: 7,
            fontSize: 11,
            color: 'var(--accent)',
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            📁 {activeWs.name}
          </div>
        )}

        {/* Nav */}
        <nav style={{ padding: '10px 10px', flex: 1 }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 8, marginBottom: 2,
                textDecoration: 'none', fontSize: 13, fontWeight: 600,
                color: isActive ? 'var(--accent)' : 'var(--muted)',
                background: isActive ? '#4f8ef711' : 'transparent',
                transition: 'all 0.15s'
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Coming soon notice */}
        <div style={{
          margin: '0 10px 10px',
          padding: '8px 10px',
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          borderRadius: 7,
          fontSize: 11,
          color: 'var(--muted)'
        }}>
          🔧 Workspace persistence coming soon
        </div>

        {/* Footer */}
        <div style={{
          padding: '8px 16px 14px',
          fontSize: 11,
          color: 'var(--muted)',
          flexShrink: 0
        }}>
          For guidance only. Always consult a qualified lawyer.
        </div>
      </aside>

      {/* Main content */}
      <main style={{
        flex: 1, overflow: 'auto',
        display: 'flex', flexDirection: 'column'
      }}>
        <Outlet />
      </main>
    </div>
  )
}