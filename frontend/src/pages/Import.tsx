import { useState, useRef, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { ImportLog } from '../types'

type Result = { status: string; institution: string; account_id: number; rows_imported: number; rows_skipped: number; error?: string }

export default function Import() {
  const { data: logs, refetch } = useApi<ImportLog[]>(() => api.get('/watcher/log'), [])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
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

  return (
    <div>
      <h1 className="page-title">Import</h1>

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
              ['Watch folder', 'Drop files into data/watch/ and they\'ll be auto-ingested on startup or when detected.'],
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
                      color: l.status === 'success' ? 'var(--green)' : l.status === 'error' ? 'var(--red)' : 'var(--text-3)',
                    }}>{l.status}</span>
                  </td>
                  <td className="num" style={{ textAlign: 'right' }}>{l.rows_imported}</td>
                  <td className="num" style={{ textAlign: 'right', color: 'var(--text-3)' }}>{l.rows_skipped}</td>
                  <td className="num" style={{ fontSize: 12, color: 'var(--text-3)' }}>
                    {l.created_at ? new Date(l.created_at).toLocaleDateString() : '—'}
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
