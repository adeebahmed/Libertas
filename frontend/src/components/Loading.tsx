interface LoadingProps {
  label?: string
}

export default function Loading({ label = 'Loading…' }: LoadingProps) {
  return (
    <div className="empty">
      <span className="spinner" aria-label={label} />
      <div className="empty-sub" style={{ marginTop: 10 }}>{label}</div>
    </div>
  )
}
