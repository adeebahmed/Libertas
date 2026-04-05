import { useState, useRef, useCallback, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { ImportLog } from '../types'

type Result = { id?: number; status: string; institution: string; account_id: number; rows_imported: number; rows_skipped: number; error?: string }

// ── Watch notification banner ──────────────────────────────────────────────
function WatchNotification({ onNewImport }: { onNewImport: () => void }) {
  const [banner, setBanner] = useState<{ id: number; filename: string; rows: number } | null>(null)
  const lastSeenId = useRef<number | null>(null)

  useEffect(() => {
    let mounted = true
    const poll = async () => {
      if (!mounted) return
      try {
        const latest = await api.get<{ id: number; filename: string; rows_imported: number; status: string } | null>('/watcher/latest')
        if (latest && latest.status === 'success') {
          if (lastSeenId.current === null) {
            lastSeenId.current = latest.id
          } else if (latest.id > lastSeenId.current) {
            lastSeenId.current = latest.id
            setBanner({ id: latest.id, filename: latest.filename, rows: latest.rows_imported })
            onNewImport()
            setTimeout(() => setBanner(null), 8000)
          }
        }
      } catch {}
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => { mounted = false; clearInterval(interval) }
  }, [onNewImport])

  if (!banner) return null
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 100,
      background: 'var(--bg-elevated)', border: '1px solid var(--gold-dim)',
      borderRadius: 8, padding: '12px 18px', boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', gap: 12, fontSize: 13,
    }}>
      <span style={{ color: 'var(--green)', fontSize: 16 }}>✓</span>
      <div>
        <div style={{ fontWeight: 500, color: 'var(--text)' }}>File auto-ingested</div>
        <div style={{ color: 'var(--text-3)', fontSize: 12 }}>{banner.filename} · {banner.rows} rows</div>
      </div>
      <button
        onClick={() => setBanner(null)}
        style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', fontSize: 16, lineHeight: 1 }}
      >×</button>
    </div>
  )
}

export default function Import() {
  const { data: logs, refetch } = useApi<ImportLog[]>(() => api.get('/watcher/log'), [])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [rollingBack, setRollingBack] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(async (f: File) => {
    setUploading(true)
    setResult(null)
    const fd = new FormData()
    fd.append('file', f)
    try {
      const r = await api.upload<Result>('/imports/upload', fd)
      setResult(r)
      refetch()
    } catch (e: any) {
      setResult({ status: 'error', institution: '', account_id: 0, rows_imported: 0, rows_skipped: 0, error: e.message })
    } finally {
      setUploading(false)
    }
  }, [refetch])

  const handleRollback = async (logId: number) => {
    if (!confirm('Roll back this import? This will delete all transactions from this import and rebuild the account.')) return
    setRollingBack(logId)
    try {
      await api.post(`/imports/${logId}/rollback`)
      refetch()
    } catch (e: any) {
      alert(`Rollback failed: ${e.message}`)
    } finally {
      setRollingBack(null)
    }
  }

  return (
    <div>
      <h1 className="page-title">Import</h1>

      <WatchNotification onNewImport={refetch} />

      <div className="grid-2 mb-32" style={{ gridTemplateColumns: '1fr 380px', alignItems: 'start' }}>
        {/* Drop zone */}
        <div>
          <div
            className={`dropzone${dragging ? ' over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]) }}
            onClick={() => fileRef.current?.click()}
          >
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }}
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
            <div className="dropzone-icon">{uploading ? '⟳' : '↑'}</div>
            <div className="dropzone-title">{uploading ? 'Processing…' : 'Drop a file here'}</div>
            <div className="dropzone-sub">CSV or Excel from any brokerage · or drop directly into data/watch/</div>
          </div>

          {result && (
            <div className="card mt-16" style={{ borderColor: result.status === 'error' ? 'var(--red)' : 'var(--gold-dim)' }}>
              {result.status === 'error' ? (
                <div style={{ color: 'var(--red)', fontSize: 14 }}>Error: {result.error}</div>
              ) : (
                <div style={{ fontSize: 14 }}>
                  <div style={{ fontWeight: 500, marginBottom: 8 }}>
                    {result.status === 'success' ? '✓' : '·'} {result.institution || 'Unknown institution'}
                  </div>
                  <div style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                    {result.rows_imported} rows imported · {result.rows_skipped} skipped (duplicates)
                  </div>
                  {result.id && (
                    <button className="btn btn-sm mt-12" onClick={() => handleRollback(result.id!)}>
                      Undo this import
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="card" style={{ padding: '24px 28px' }}>
          <div className="section-label mb-16">How it works</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
              ['Drop any file', 'CSV or Excel from any brokerage. No column mapping required.'],
              ['Auto-detection', 'Libertas reads the data and figures out what each column is.'],
              ['Filename matters', 'Name like "Fidelity_Roth_IRA.csv" — institution and account type are inferred from the filename.'],
              ['Watch folder', 'Drop files into data/watch/ and they\'ll be auto-ingested. A notification will appear here.'],
              ['Rollback', 'Made a mistake? Click "Rollback" on any import to undo it.'],
            ].map(([title, desc]) => (
              <div key={title}>
                <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{title}</div>
                <div style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.55 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Import log */}
      <div className="section-label mb-16">Import history</div>
      {logs && logs.length > 0 ? (
        <div className="card" style={{ padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>File</th>
                <th>Institution</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Imported</th>
                <th style={{ textAlign: 'right' }}>Skipped</th>
                <th>When</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>{l.filename}</td>
                  <td style={{ color: 'var(--text-2)' }}>{l.institution_name ?? '—'}</td>
                  <td>
                    <span style={{
                      fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.4px',
                      color: l.status === 'success' ? 'var(--green)' : l.status === 'rolled_back' ? 'var(--text-3)' : l.status === 'error' ? 'var(--red)' : 'var(--text-3)',
                    }}>{l.status === 'rolled_back' ? 'rolled back' : l.status}</span>
                  </td>
                  <td className="num" style={{ textAlign: 'right' }}>{l.rows_imported}</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--text-3)' }}>{l.rows_skipped}</td>
                  <td className="num" style={{ fontSize: 12, color: 'var(--text-3)' }}>
                    {l.created_at ? new Date(l.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    {l.status === 'success' && (
                      <button
                        className="btn btn-sm"
                        onClick={() => handleRollback(l.id)}
                        disabled={rollingBack === l.id}
                      >
                        {rollingBack === l.id ? '…' : 'Rollback'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
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
