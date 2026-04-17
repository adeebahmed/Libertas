import type { ReactNode } from 'react'

interface ConfirmProps {
  message: ReactNode
  detail?: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function Confirm({
  message,
  detail,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmProps) {
  return (
    <div
      role="presentation"
      onMouseDown={onCancel}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 90,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-1)',
          border: `1px solid ${destructive ? 'var(--neg)' : 'var(--border-strong)'}`,
          borderRadius: 'var(--r)',
          padding: '20px 24px',
          maxWidth: 400,
          width: '100%',
        }}
      >
        <div style={{ fontWeight: 500, fontSize: 'var(--fs-base)', marginBottom: detail ? 8 : 20 }}>
          {message}
        </div>
        {detail && (
          <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', marginBottom: 20, lineHeight: 1.5 }}>
            {detail}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="btn btn-sm" onClick={onCancel}>{cancelLabel}</button>
          <button
            className="btn btn-sm"
            onClick={onConfirm}
            style={destructive ? { color: 'var(--neg)', borderColor: 'var(--neg)' } : undefined}
          >
            {confirmLabel}
          </button>
        </div>
        <div style={{ marginTop: 12, fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-xs)', color: 'var(--text-mute)', textAlign: 'right' }}>
          [Esc] cancel · [Enter] confirm
        </div>
      </div>
    </div>
  )
}
