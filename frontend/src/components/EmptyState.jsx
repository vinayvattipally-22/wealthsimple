export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="empty-state">
      {Icon && <Icon size={56} className="empty-state-icon" strokeWidth={1.5} />}
      <div className="empty-state-title">{title}</div>
      <p className="empty-state-description">{description}</p>
      {action && <div style={{ marginTop: 'var(--space-6)' }}>{action}</div>}
    </div>
  )
}
