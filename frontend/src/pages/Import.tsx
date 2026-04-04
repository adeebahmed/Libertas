import { useState, useRef, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, Institution, ImportPreview, PendingFile } from '../types'

export default function Import() {
  const { data: accounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: institutions } = useApi<Institution[]>(() => api.get('/accounts/institutions'), [])
  const { data: pending, refetch: refetchPending } = useApi<PendingFile[]>(() => api.get('/watcher/pending'), [])

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [accountId, setAccountId] = useState<string>('')
  const [institutionId, setInstitutionId] = useState<string>('')
  const [result, setResult] = useState<{ imported: number; skipped: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const FIELDS = ['date', 'symbol', 'quantity', 'price', 'amount', 'type', 'description', '(skip)']

  const handleFile = useCallback(async (f: File) => {
    setFile(f)
    setResult(null)
    const formData = new FormData()
    formData.append('file', f)
    const p = await api.upload<ImportPreview>('/imports/preview', formData)
    setPreview(p)
    setMapping(p.suggested_mapping)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const handleConfirm = async () => {
    if (!file || !accountId) return
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('account_id', accountId)
    if (institutionId) formData.append('institution_id', institutionId)
    formData.append('column_mapping', JSON.stringify(mapping))
    const r = await api.upload<{ imported: number; skipped: number }>('/imports/confirm', formData)
    setResult(r)
    setLoading(false)
    setFile(null)
    setPreview(null)
  }

  return (
    <div>
      <h1 className="page-title">Import</h1>

      {pending && pending.length > 0 && (
        <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Detected Files</h3>
          {pending.map((p) => (
            <div key={p.path} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0' }}>
              <span style={{ fontWeight: 500 }}>{p.filename}</span>
              {p.institution_name && (
                <span className="badge badge-brokerage">{p.institution_name}</span>
              )}
              <button className="btn btn-primary" style={{ marginLeft: 'auto', padding: '4px 12px', fontSize: 13 }}
                onClick={() => {
                  // Load the pending file for import
                  refetchPending()
                }}
              >
                Import
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Institution export links */}
      {institutions && institutions.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Quick Export Links</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {institutions.filter(i => i.export_url).map((i) => (
              <a key={i.id} href={i.export_url!} target="_blank" rel="noopener" className="btn">
                {i.name}
              </a>
            ))}
          </div>
        </div>
      )}

      {!preview ? (
        <div
          className="drop-zone"
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
          onDragLeave={(e) => e.currentTarget.classList.remove('dragover')}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Drop CSV/Excel file here</p>
          <p>or click to browse</p>
        </div>
      ) : (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
            Preview: {file?.name}
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div className="form-group">
              <label>Account</label>
              <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                <option value="">Select account...</option>
                {accounts?.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Institution (optional)</label>
              <select value={institutionId} onChange={(e) => setInstitutionId(e.target.value)}>
                <option value="">None</option>
                {institutions?.map((i) => (
                  <option key={i.id} value={i.id}>{i.name}</option>
                ))}
              </select>
            </div>
          </div>

          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Column Mapping</h4>
          <table className="table" style={{ marginBottom: 16 }}>
            <thead>
              <tr>
                <th>File Column</th>
                <th>Maps To</th>
              </tr>
            </thead>
            <tbody>
              {preview.headers.map((h) => (
                <tr key={h}>
                  <td>{h}</td>
                  <td>
                    <select
                      value={mapping[h] || '(skip)'}
                      onChange={(e) => setMapping({ ...mapping, [h]: e.target.value })}
                    >
                      {FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Sample Data</h4>
          <div style={{ overflowX: 'auto', marginBottom: 16 }}>
            <table className="table">
              <thead>
                <tr>{preview.headers.map((h) => <th key={h}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, i) => (
                  <tr key={i}>{preview.headers.map((h) => <td key={h}>{row[h]}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={handleConfirm} disabled={!accountId || loading}>
              {loading ? 'Importing...' : 'Confirm Import'}
            </button>
            <button className="btn" onClick={() => { setFile(null); setPreview(null) }}>Cancel</button>
          </div>
        </div>
      )}

      {result && (
        <div className="card" style={{ marginTop: 16, borderColor: 'var(--green)' }}>
          <p>Imported <strong>{result.imported}</strong> transactions. Skipped <strong>{result.skipped}</strong> duplicates.</p>
        </div>
      )}
    </div>
  )
}
