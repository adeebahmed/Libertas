import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { ImportLog } from '../types'

type UploadResult = {
  id?: number
  status: string
  institution: string
  account_id: number
  rows_imported: number
  rows_skipped: number
  rows_failed?: number | null
  parse_errors?: number | null
  potential_transfers?: number | null
  error?: string
}

type QualityKey = 'rows_failed' | 'parse_errors' | 'potential_transfers'

const QUALITY_META: Record<QualityKey, { label: string; tone: 'danger' | 'warning' | 'info' }> = {
  rows_failed: { label: 'Failed rows', tone: 'danger' },
  parse_errors: { label: 'Parse errors', tone: 'warning' },
  potential_transfers: { label: 'Transfer warnings', tone: 'info' },
}

function qualityItems(source: Partial<Record<QualityKey, number | null | undefined>>) {
  return (Object.keys(QUALITY_META) as QualityKey[])
    .map((key) => {
      const value = source[key]
      if (value == null || value <= 0) return null
      return { key, label: QUALITY_META[key].label, tone: QUALITY_META[key].tone, value }
    })
    .filter((item): item is { key: QualityKey; label: string; tone: 'danger' | 'warning' | 'info'; value: number } => item !== null)
}

function QualityBadges({ source }: { source: Partial<Record<QualityKey, number | null | undefined>> }) {
  const items = qualityItems(source)
  if (!items.length) return <span style={{ color: 'var(--text-3)', fontSize: 'var(--fs-sm)' }}>—</span>

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' }}>
      {items.map((item) => (
        <span
          key={item.key}
          className="tag"
          style={{
            color: item.tone === 'danger' ? 'var(--neg)' : 'var(--accent)',
            borderColor: item.tone === 'danger' ? '#f8717128' : item.tone === 'warning' ? '#d4a84028' : '#60a5fa28',
            background: item.tone === 'danger' ? '#f871710c' : item.tone === 'warning' ? '#d4a8400c' : '#60a5fa0c',
            textTransform: 'none',
            letterSpacing: 0,
            fontSize: 'var(--fs-xs)',
            padding: '2px 7px',
          }}
          title={`${item.label}: ${item.value}`}
        >
          {item.label} {item.value}
        </span>
      ))}
    </div>
  )
}

function WatchNotification({ onNewImport }: { onNewImport: () => void }) {
  const [banner, setBanner] = useState<{ id: number; filename: string; rows: number } | null>(null)
  const lastSeenId = useRef<number | null>(null)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    let mounted = true

    const poll = async () => {
      if (!mounted) return
      try {
        const latest = await api.get<{ id: number; filename: string; rows_imported: number; status: string } | null>('/watcher/latest')
        if (!latest || latest.status !== 'success') return
        if (lastSeenId.current === null) {
          lastSeenId.current = latest.id
          return
        }
        if (latest.id > lastSeenId.current) {
          lastSeenId.current = latest.id
          setBanner({ id: latest.id, filename: latest.filename, rows: latest.rows_imported })
          onNewImport()
          if (timerRef.current) window.clearTimeout(timerRef.current)
          timerRef.current = window.setTimeout(() => setBanner(null), 8000)
        }
      } catch {
        // Keep polling quietly if the watcher endpoint is temporarily unavailable.
      }
    }

    poll()
    const interval = window.setInterval(poll, 5000)

    return () => {
      mounted = false
      window.clearInterval(interval)
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [onNewImport])

  if (!banner) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 100,
        background: 'var(--bg-2)',
        border: '1px solid var(--accent-dim)',
        borderRadius: 'var(--r)',
        padding: '12px 18px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        fontSize: 'var(--fs-base)',
      }}
    >
      <span style={{ color: 'var(--pos)', fontSize: 'var(--fs-md)' }}>✓</span>
      <div>
        <div style={{ fontWeight: 500, color: 'var(--text)' }}>File auto-ingested</div>
        <div style={{ color: 'var(--text-3)', fontSize: 'var(--fs-sm)' }}>{banner.filename} · {banner.rows} rows</div>
      </div>
      <button
        type="button"
        onClick={() => setBanner(null)}
        style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', fontSize: 'var(--fs-md)', lineHeight: 1 }}
      >
        ×
      </button>
    </div>
  )
}

export default function Import() {
  const { data: logs, refetch } = useApi<ImportLog[]>(() => api.get('/watcher/log'), [])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [rollingBack, setRollingBack] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    async (file: File) => {
      setUploading(true)
      setResult(null)
      const fd = new FormData()
      fd.append('file', file)
      try {
        const response = await api.upload<UploadResult>('/imports/upload', fd)
        setResult(response)
        refetch()
      } catch (error: any) {
        setResult({
          status: 'error',
          institution: '',
          account_id: 0,
          rows_imported: 0,
          rows_skipped: 0,
          error: error.message,
        })
      } finally {
        setUploading(false)
      }
    },
    [refetch],
  )

  const handleRollback = async (logId: number) => {
    if (!window.confirm("Roll back this import? All transactions from this file will be removed. The account remains; only this import's data is undone.")) return
    setRollingBack(logId)
    try {
      await api.post(`/imports/${logId}/rollback`)
      refetch()
    } catch (error: any) {
      window.alert(`Rollback failed: ${error.message}`)
    } finally {
      setRollingBack(null)
    }
  }

  const latestLogs = useMemo(() => {
    if (!logs) return []
    return logs.reduce<ImportLog[]>((acc, log) => {
      if (!acc.some((item) => item.filename === log.filename)) acc.push(log)
      return acc
    }, [])
  }, [logs])

  return (
    <div>
      <h1 className="page-title">Import</h1>

      <WatchNotification onNewImport={refetch} />

      <div className="grid-2 import-top-grid mb-32" style={{ gridTemplateColumns: '1fr 380px', alignItems: 'start' }}>
        <div>
          <div
            className={`dropzone${dragging ? ' over' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              const file = e.dataTransfer.files[0]
              if (file) void handleFile(file)
            }}
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ display: 'none' }}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void handleFile(file)
              }}
            />
            <div className="dropzone-icon">{uploading ? '⟳' : '↑'}</div>
            <div className="dropzone-title">{uploading ? 'Processing…' : 'Drop a file here'}</div>
            <div className="dropzone-sub">CSV or Excel from any brokerage · or drop directly into data/watch/</div>
          </div>

          {result && (
            <div className="card mt-16" style={{ borderColor: result.status === 'error' ? 'var(--neg)' : 'var(--accent-dim)' }}>
              {result.status === 'error' ? (
                <div style={{ color: 'var(--neg)', fontSize: 'var(--fs-base)' }}>Error: {result.error}</div>
              ) : (
                <div style={{ fontSize: 'var(--fs-base)' }}>
                  <div style={{ fontWeight: 500, marginBottom: 8 }}>
                    {result.status === 'success' ? '✓' : '·'} {result.institution || 'Unknown institution'}
                  </div>
                  <div style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-base)' }}>
                    {result.rows_imported} rows imported · {result.rows_skipped} skipped (duplicates)
                  </div>
                  <div className="flex-between" style={{ marginTop: 12, gap: 12, alignItems: 'start' }}>
                    <div>
                      <div className="section-label mb-8">Quality</div>
                      <QualityBadges source={result} />
                    </div>
                    {result.id && (
                      <button className="btn btn-sm" onClick={() => handleRollback(result.id!)}>
                        Undo this import
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card import-guide-card" style={{ padding: '24px 28px' }}>
          <div className="section-label mb-16">How it works</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
              ['Drop any file', 'CSV or Excel from any brokerage. No column mapping required.'],
              ['Auto-detection', 'Libertas reads the data and figures out what each column is.'],
              ['Filename matters', 'Name like "Fidelity_Roth_IRA.csv" — institution and account type are inferred from the filename.'],
              ['Watch folder', 'Drop files into data/watch/ and they will be auto-ingested. A notification will appear here.'],
              ['Rollback', 'Made a mistake? Click "Rollback" on any import to undo it.'],
            ].map(([title, desc]) => (
              <div key={title}>
                <div style={{ fontSize: 'var(--fs-base)', fontWeight: 500, marginBottom: 4 }}>{title}</div>
                <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', lineHeight: 1.55 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="section-label mb-16">Import history</div>
      {latestLogs.length > 0 ? (
        <div className="card" style={{ padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>File</th>
                <th>Institution</th>
                <th>Status</th>
                <th>Quality</th>
                <th style={{ textAlign: 'right' }}>Imported</th>
                <th style={{ textAlign: 'right' }}>Skipped</th>
                <th>When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {latestLogs.map((log) => {
                const isDuplicateOnly = log.status === 'success' && log.rows_imported === 0 && log.rows_skipped > 0
                const statusLabel = isDuplicateOnly ? 'duplicate' : log.status === 'rolled_back' ? 'rolled back' : log.status
                const statusColor =
                  log.status === 'error'
                    ? 'var(--neg)'
                    : isDuplicateOnly
                      ? 'var(--text-2)'
                      : log.status === 'success'
                        ? 'var(--pos)'
                        : 'var(--text-3)'

                return (
                  <tr key={log.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-sm)' }}>{log.filename}</td>
                    <td style={{ color: 'var(--text-2)' }}>{log.institution_name ?? '—'}</td>
                    <td>
                      <span
                        style={{
                          fontSize: 'var(--fs-xs)',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.4px',
                          color: statusColor,
                        }}
                      >
                        {statusLabel}
                      </span>
                      {log.status === 'error' && log.error_message && (
                        <div style={{ marginTop: 4, fontSize: 'var(--fs-xs)', color: 'var(--text-3)', maxWidth: 280, lineHeight: 1.35 }}>
                          {log.error_message}
                        </div>
                      )}
                    </td>
                    <td><QualityBadges source={log} /></td>
                    <td className="num" style={{ textAlign: 'right' }}>{log.rows_imported}</td>
                    <td className="num" style={{ textAlign: 'right', color: 'var(--text-3)' }}>{log.rows_skipped}</td>
                    <td className="num" style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>
                      {log.created_at ? new Date(log.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td>
                      {log.status === 'success' && (
                        <button className="btn btn-sm" onClick={() => handleRollback(log.id)} disabled={rollingBack === log.id}>
                          {rollingBack === log.id ? '…' : 'Rollback'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">
          <div className="empty-title">No imports yet</div>
          <div className="empty-sub">Drop a file above to get started</div>
        </div>
      )}
    </div>
  )
}
