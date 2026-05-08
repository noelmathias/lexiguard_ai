// Loading spinner
export default function LoadingSpinner({ label = 'Processing...' }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', gap: 16, padding: 40, color: 'var(--muted)'
    }}>
      <div style={{
        width: 36, height: 36,
        border: '3px solid var(--border)',
        borderTopColor: 'var(--accent)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <span style={{ fontSize: 14 }}>{label}</span>
    </div>
  )
}