import type { ReactNode } from 'react'

interface EmptyProps {
  icon?: string
  title: string
  sub?: string
  action?: ReactNode
}

export default function Empty({ icon = '◌', title, sub, action }: EmptyProps) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {sub && <div className="empty-sub">{sub}</div>}
      {action}
    </div>
  )
}
