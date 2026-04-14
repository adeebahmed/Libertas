import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { Account, AccountDetail, AccountPerformance, AccountType, DebtResponse, Holding, Property, Transaction } from '../types'

const ACCOUNT_TYPES: AccountType[] = [
  'brokerage',
  'crypto',
  'savings',
  'hsa',
  'roth_ira',
  '401k',
  'checking',
  'credit_card',
  'student_loan',
  'auto_loan',
  'personal_loan',
  'mortgage',
  'real_estate',
  'other',
]

const INVESTMENT_TYPES = new Set<AccountType>(['brokerage', 'crypto', 'hsa', 'roth_ira', '401k'])
const DEBT_TYPES = new Set<AccountType>(['credit_card', 'student_loan', 'auto_loan', 'personal_loan', 'mortgage'])
const TRANSACTION_TYPES = [
  'manual',
  'buy',
  'sell',
  'deposit',
  'withdrawal',
  'transfer_in',
  'transfer_out',
  'dividend',
  'interest',
  'fee',
  'adjustment',
] as const

type ModalState =
  | { kind: 'account'; mode: 'create' }
  | { kind: 'account'; mode: 'edit'; account: Account }
  | { kind: 'balance'; account: Account }
  | { kind: 'transaction'; mode: 'create'; account: Account }
  | { kind: 'transaction'; mode: 'edit'; account: Account; transaction: Transaction }
  | { kind: 'holding'; mode: 'create'; account: Account }
  | { kind: 'holding'; mode: 'edit'; account: Account; holding: Holding }

type Freshness = {
  label: string
  tone: 'green' | 'gold' | 'red' | 'neutral'
  title: string
}

function usd(value: number | null | undefined) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value ?? 0)
}

function qty(value: number | null | undefined) {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(value)
}

function percent(value: number | null | undefined) {
  if (value == null) return '—'
  return `${value.toFixed(2)}%`
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function toNumber(value: string) {
  if (value.trim() === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString()
}

function formatAge(value: string | null | undefined): Freshness {
  if (!value) {
    return { label: 'No update', tone: 'neutral', title: 'This account has never been refreshed.' }
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return { label: 'Unknown', tone: 'neutral', title: value }
  }
  const ageDays = Math.max(0, Math.floor((Date.now() - date.getTime()) / 86_400_000))
  if (ageDays <= 1) {
    return { label: ageDays === 0 ? 'Fresh' : '1d old', tone: 'green', title: `Updated ${ageDays === 0 ? 'today' : 'yesterday'}` }
  }
  if (ageDays <= 7) return { label: `${ageDays}d old`, tone: 'green', title: `Updated ${ageDays} days ago` }
  if (ageDays <= 30) return { label: `${ageDays}d old`, tone: 'gold', title: `Updated ${ageDays} days ago` }
  return { label: `${ageDays}d old`, tone: 'red', title: `Updated ${ageDays} days ago` }
}

function humanize(value: string) {
  return value.replace(/_/g, '\u00A0') // non-breaking space — prevents tag wrapping
}

function isImportedTransaction(txn: Transaction) {
  return Object.prototype.hasOwnProperty.call(txn, 'import_log_id') && txn.import_log_id != null
}

function AccountTag({ type }: { type: AccountType }) {
  const fallback: Record<string, { color: string; borderColor: string; background: string }> = {
    mortgage: { color: 'var(--red)', borderColor: '#f8717128', background: '#f871710c' },
    other: { color: 'var(--text-2)', borderColor: '#7898b828', background: '#7898b80c' },
  }

  return (
    <span className={`tag tag-${type}`} style={fallback[type] ?? undefined}>
      {humanize(type)}
    </span>
  )
}

function FreshnessDot({ lastUpdated }: { lastUpdated: string | null }) {
  const freshness = formatAge(lastUpdated)
  const color =
    freshness.tone === 'green'
      ? 'var(--green)'
      : freshness.tone === 'gold'
        ? 'var(--gold)'
        : freshness.tone === 'red'
          ? 'var(--red)'
          : 'var(--text-3)'

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--text-2)', fontSize: 12 }} title={freshness.title}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: color,
          boxShadow: `0 0 0 3px ${color}18`,
          flexShrink: 0,
        }}
      />
      {freshness.label}
    </span>
  )
}

function Badge({ label, tone, title }: { label: string; tone: 'red' | 'gold' | 'blue' | 'green' | 'neutral'; title?: string }) {
  const styles: Record<typeof tone, { color: string; borderColor: string; background: string }> = {
    red: { color: 'var(--red)', borderColor: '#f8717128', background: '#f871710c' },
    gold: { color: 'var(--gold)', borderColor: '#d4a84028', background: '#d4a8400c' },
    blue: { color: 'var(--blue-bright)', borderColor: '#60a5fa28', background: '#60a5fa0c' },
    green: { color: 'var(--green)', borderColor: '#34d39928', background: '#34d3990c' },
    neutral: { color: 'var(--text-2)', borderColor: '#7898b828', background: '#7898b80c' },
  }

  return (
    <span
      className="tag"
      title={title}
      style={{
        ...styles[tone],
        textTransform: 'none',
        letterSpacing: 0,
        fontSize: 10.5,
        padding: '2px 7px',
      }}
    >
      {label}
    </span>
  )
}

type ActionItem = { label: string; onClick: () => void; destructive?: boolean }

function ActionsMenu({ items, disabled }: { items: ActionItem[]; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [open])

  return (
    <div ref={ref} className="row-actions" style={{ position: 'relative', display: 'inline-block' }} onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        aria-label="Actions"
        style={{
          background: 'transparent',
          border: '1px solid transparent',
          borderRadius: 6,
          color: 'var(--text-3)',
          cursor: 'pointer',
          fontSize: 16,
          lineHeight: 1,
          padding: '2px 6px',
          transition: 'border-color 0.15s, color 0.15s',
        }}
        onMouseEnter={(e) => {
          const b = e.currentTarget as HTMLButtonElement
          b.style.borderColor = 'var(--border)'
          b.style.color = 'var(--text)'
        }}
        onMouseLeave={(e) => {
          const b = e.currentTarget as HTMLButtonElement
          b.style.borderColor = 'transparent'
          b.style.color = 'var(--text-3)'
        }}
      >
        ···
      </button>
      {open && (
        <div style={{
          position: 'absolute',
          right: 0,
          top: 'calc(100% + 4px)',
          zIndex: 50,
          minWidth: 130,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          overflow: 'hidden',
        }}>
          {items.map((item, i) => (
            <button
              key={item.label}
              onClick={() => { item.onClick(); setOpen(false) }}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                padding: '9px 14px',
                fontSize: 13,
                fontWeight: 450,
                color: item.destructive ? 'var(--red)' : 'var(--text)',
                background: 'transparent',
                border: 'none',
                borderBottom: i < items.length - 1 ? '1px solid var(--border-soft)' : 'none',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.04)' }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ModalShell({
  title,
  subtitle,
  onClose,
  children,
  width = 720,
}: {
  title: string
  subtitle?: string
  onClose: () => void
  children: ReactNode
  width?: number
}) {
  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        background: 'rgba(4, 8, 17, 0.72)',
        backdropFilter: 'blur(6px)',
        display: 'grid',
        placeItems: 'center',
        padding: 16,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: `min(100%, ${width}px)`,
          maxHeight: 'min(90vh, 900px)',
          overflow: 'auto',
          borderRadius: 16,
          border: '1px solid var(--border)',
          background: 'linear-gradient(180deg, rgba(17,24,39,0.98), rgba(12,15,26,0.98))',
          boxShadow: '0 28px 70px rgba(0,0,0,0.45)',
          padding: 24,
        }}
      >
        <div className="flex-between gap-12 mb-8" style={{ alignItems: 'start' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 600, lineHeight: 1.1 }}>{title}</div>
            {subtitle && <div style={{ marginTop: 6, color: 'var(--text-3)', fontSize: 13, lineHeight: 1.45 }}>{subtitle}</div>}
          </div>
          <button type="button" className="btn btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export default function Accounts() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: accounts, loading: accountsLoading, refetch: refetchAccounts } = useApi<Account[]>(() => api.get('/accounts'), [])
  const { data: debtData, refetch: refetchDebts } = useApi<DebtResponse>(() => api.get('/debt'), [])
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const value = searchParams.get('accountId')
    if (!value) return null
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  })
  const [txSearch, setTxSearch] = useState('')
  const [txTypeFilter, setTxTypeFilter] = useState('')
  const [txMinAmount, setTxMinAmount] = useState('')
  const [txMaxAmount, setTxMaxAmount] = useState('')
  const [txFromDate, setTxFromDate] = useState('')
  const [txToDate, setTxToDate] = useState('')
  const { data: detail, loading: detailLoading, refetch: refetchDetail } = useApi<AccountDetail | null>(
    () => (selectedId ? api.get(`/accounts/${selectedId}`) : Promise.resolve(null)),
    [selectedId],
  )
  const txQuery = useMemo(() => {
    if (!selectedId) return ''
    const params = new URLSearchParams({ limit: '500' })
    if (txSearch.trim()) params.set('search', txSearch.trim())
    if (txTypeFilter) params.set('type', txTypeFilter)
    if (txFromDate) params.set('date_from', txFromDate)
    if (txToDate) params.set('date_to', txToDate)
    if (txMinAmount.trim()) params.set('min_amount', txMinAmount.trim())
    if (txMaxAmount.trim()) params.set('max_amount', txMaxAmount.trim())
    return params.toString()
  }, [selectedId, txSearch, txTypeFilter, txFromDate, txToDate, txMinAmount, txMaxAmount])

  const { data: transactions, refetch: refetchTransactions } = useApi<Transaction[]>(
    () => (selectedId ? api.get(`/accounts/${selectedId}/transactions?${txQuery}`) : Promise.resolve([])),
    [selectedId, txQuery],
  )
  const { data: performance } = useApi<AccountPerformance | null>(
    () => (selectedId ? api.get(`/accounts/${selectedId}/performance`) : Promise.resolve(null)),
    [selectedId],
  )
  const { data: properties } = useApi<Property[]>(() => api.get('/real-estate'), [])

  const [modal, setModal] = useState<ModalState | null>(null)
  const [accountDraft, setAccountDraft] = useState({ name: '', type: 'brokerage' as AccountType, institution_id: '', currency: 'USD' })
  const [balanceDraft, setBalanceDraft] = useState({ balance: '', date: todayIso() })
  const [transactionDraft, setTransactionDraft] = useState({
    id: null as number | null,
    date: todayIso(),
    type: 'manual',
    symbol: '',
    quantity: '',
    price: '',
    amount: '',
    description: '',
  })
  const [holdingDraft, setHoldingDraft] = useState({
    id: null as number | null,
    symbol: '',
    quantity: '',
    cost_basis: '',
    last_price: '',
  })
  const [debtDraft, setDebtDraft] = useState({ interest_rate: '', minimum_payment: '', payoff_date: '' })
  const [saving, setSaving] = useState(false)

  const sortedAccounts = useMemo(() => {
    return [...(accounts ?? [])].sort((a, b) => b.balance - a.balance)
  }, [accounts])

  const totalBalance = useMemo(() => sortedAccounts.reduce((sum, account) => sum + account.balance, 0), [sortedAccounts])

  const activeAccount = useMemo(() => {
    if (selectedId == null) return null
    return detail ?? sortedAccounts.find((account) => account.id === selectedId) ?? null
  }, [detail, selectedId, sortedAccounts])

  const activeDebt = useMemo(() => {
    return debtData?.debts.find((debt) => debt.account_id === activeAccount?.id) ?? null
  }, [activeAccount?.id, debtData])

  const activeFreshness = formatAge(activeAccount?.last_updated ?? null)
  const activeProperties = useMemo(
    () => (properties ?? []).filter((property) => property.account_id === activeAccount?.id),
    [properties, activeAccount?.id],
  )
  const holdingsTotal = useMemo(
    () => (detail?.holdings ?? []).reduce((sum, holding) => sum + (holding.market_value ?? 0), 0),
    [detail?.holdings],
  )

  useEffect(() => {
    const current = searchParams.get('accountId')
    const next = selectedId == null ? null : String(selectedId)
    if (current === next) return

    const nextParams = new URLSearchParams(searchParams)
    if (next == null) nextParams.delete('accountId')
    else nextParams.set('accountId', next)
    setSearchParams(nextParams, { replace: true })
  }, [selectedId, searchParams, setSearchParams])

  useEffect(() => {
    if (!activeDebt) {
      setDebtDraft({ interest_rate: '', minimum_payment: '', payoff_date: '' })
      return
    }

    setDebtDraft({
      interest_rate: String(activeDebt.interest_rate ?? ''),
      minimum_payment: String(activeDebt.minimum_payment ?? ''),
      payoff_date: activeDebt.payoff_date ?? '',
    })
  }, [activeDebt?.account_id, activeDebt?.interest_rate, activeDebt?.minimum_payment, activeDebt?.payoff_date])

  function closeModal() {
    setModal(null)
  }

  function openAccountCreate() {
    setAccountDraft({ name: '', type: 'brokerage', institution_id: '', currency: 'USD' })
    setModal({ kind: 'account', mode: 'create' })
  }

  function openAccountEdit(account: Account) {
    setAccountDraft({
      name: account.name,
      type: account.type,
      institution_id: account.institution_id == null ? '' : String(account.institution_id),
      currency: account.currency || 'USD',
    })
    setModal({ kind: 'account', mode: 'edit', account })
  }

  function openBalanceModal(account: Account) {
    setBalanceDraft({ balance: String(account.balance ?? 0), date: todayIso() })
    setModal({ kind: 'balance', account })
  }

  function openTransactionCreate(account: Account) {
    setTransactionDraft({
      id: null,
      date: todayIso(),
      type: 'manual',
      symbol: '',
      quantity: '',
      price: '',
      amount: '',
      description: '',
    })
    setModal({ kind: 'transaction', mode: 'create', account })
  }

  function openTransactionEdit(account: Account, transaction: Transaction) {
    setTransactionDraft({
      id: transaction.id,
      date: transaction.date,
      type: transaction.type,
      symbol: transaction.symbol ?? '',
      quantity: transaction.quantity == null ? '' : String(transaction.quantity),
      price: transaction.price == null ? '' : String(transaction.price),
      amount: transaction.amount == null ? '' : String(transaction.amount),
      description: transaction.description ?? '',
    })
    setModal({ kind: 'transaction', mode: 'edit', account, transaction })
  }

  function openHoldingCreate(account: Account) {
    setHoldingDraft({ id: null, symbol: '', quantity: '', cost_basis: '', last_price: '' })
    setModal({ kind: 'holding', mode: 'create', account })
  }

  function openHoldingEdit(account: Account, holding: Holding) {
    setHoldingDraft({
      id: holding.id,
      symbol: holding.symbol,
      quantity: String(holding.quantity ?? 0),
      cost_basis: holding.cost_basis == null ? '' : String(holding.cost_basis),
      last_price: holding.last_price == null ? '' : String(holding.last_price),
    })
    setModal({ kind: 'holding', mode: 'edit', account, holding })
  }

  async function refreshAll() {
    await Promise.all([refetchAccounts(), refetchDetail(), refetchTransactions(), refetchDebts()])
  }

  async function saveAccount() {
    if (!modal || modal.kind !== 'account') return
    if (!accountDraft.name.trim()) return

    setSaving(true)
    try {
      const payload = {
        name: accountDraft.name.trim(),
        type: accountDraft.type,
        institution_id: accountDraft.institution_id ? Number(accountDraft.institution_id) : null,
        currency: accountDraft.currency.trim() || 'USD',
      }

      if (modal.mode === 'create') {
        const created = await api.post<Account>('/accounts', payload)
        setSelectedId(created.id)
      } else {
        await api.patch(`/accounts/${modal.account.id}`, payload)
        setSelectedId(modal.account.id)
      }

      closeModal()
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function deleteAccount(account: Account) {
    if (!window.confirm(`Delete ${account.name}? This cannot be undone.`)) return
    setSaving(true)
    try {
      await api.delete(`/accounts/${account.id}`)
      if (selectedId === account.id) setSelectedId(null)
      closeModal()
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function saveBalance() {
    if (!modal || modal.kind !== 'balance') return
    const balance = toNumber(balanceDraft.balance)
    if (balance == null) return

    setSaving(true)
    try {
      await api.post(`/accounts/${modal.account.id}/balance`, {
        balance,
        date: balanceDraft.date || todayIso(),
      })
      closeModal()
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function saveTransaction() {
    if (!modal || modal.kind !== 'transaction') return

    const payload = {
      date: transactionDraft.date || todayIso(),
      type: transactionDraft.type.trim() || 'manual',
      symbol: transactionDraft.symbol.trim() || null,
      quantity: toNumber(transactionDraft.quantity),
      price: toNumber(transactionDraft.price),
      amount: toNumber(transactionDraft.amount),
      description: transactionDraft.description.trim() || null,
    }

    setSaving(true)
    try {
      if (modal.mode === 'create') {
        await api.post(`/accounts/${modal.account.id}/transactions`, payload)
      } else {
        await api.patch(`/accounts/${modal.account.id}/transactions/${transactionDraft.id}`, payload)
      }
      closeModal()
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function deleteTransaction(account: Account, transaction: Transaction) {
    if (!window.confirm('Delete this transaction?')) return
    setSaving(true)
    try {
      await api.delete(`/accounts/${account.id}/transactions/${transaction.id}`)
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function saveHolding() {
    if (!modal || modal.kind !== 'holding') return

    const symbol = holdingDraft.symbol.trim()
    const quantity = toNumber(holdingDraft.quantity)
    if (!symbol || quantity == null) return

    const payload = {
      symbol,
      quantity,
      cost_basis: toNumber(holdingDraft.cost_basis),
      last_price: toNumber(holdingDraft.last_price),
    }

    setSaving(true)
    try {
      if (modal.mode === 'create') {
        await api.post(`/accounts/${modal.account.id}/holdings`, payload)
      } else {
        await api.patch(`/accounts/${modal.account.id}/holdings/${holdingDraft.id}`, payload)
      }
      closeModal()
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function deleteHolding(account: Account, holding: Holding) {
    if (!window.confirm(`Delete holding ${holding.symbol}?`)) return
    setSaving(true)
    try {
      await api.delete(`/accounts/${account.id}/holdings/${holding.id}`)
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  async function saveDebt() {
    if (!activeAccount || !DEBT_TYPES.has(activeAccount.type)) return
    setSaving(true)
    try {
      await api.patch(`/debt/${activeAccount.id}`, {
        interest_rate: toNumber(debtDraft.interest_rate) ?? 0,
        minimum_payment: toNumber(debtDraft.minimum_payment) ?? 0,
        payoff_date: debtDraft.payoff_date || null,
      })
      await refreshAll()
    } finally {
      setSaving(false)
    }
  }

  const accountCount = accounts?.length ?? 0

  return (
    <div>
      <div className="flex-between accounts-header mb-24" style={{ alignItems: 'end' }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: 4 }}>Accounts</h1>
          <div style={{ color: 'var(--text-3)', fontSize: 13 }}>
            {accountCount} {accountCount === 1 ? 'account' : 'accounts'} · {usd(totalBalance)} total balance
          </div>
        </div>
        <button className="btn btn-primary" onClick={openAccountCreate}>Add account</button>
      </div>

      <div className="grid-2 accounts-layout mb-24" style={{ gridTemplateColumns: 'minmax(360px, 1fr) minmax(0, 1.25fr)', alignItems: 'start' }}>
        <div className="card" style={{ padding: 0 }}>
          <div className="flex-between" style={{ padding: '18px 20px 14px', borderBottom: '1px solid var(--border-soft)' }}>
            <div>
              <div className="section-label mb-8">Accounts</div>
              <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>Select an account to inspect holdings, debt, and activity.</div>
            </div>
          </div>

          {accountsLoading ? (
            <div style={{ padding: 24, color: 'var(--text-3)', fontSize: 13 }}>Loading accounts…</div>
          ) : sortedAccounts.length > 0 ? (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Type</th>
                  <th style={{ textAlign: 'right' }}>Balance</th>
                  <th>Freshness</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedAccounts.map((account) => {
                  const isActive = account.id === selectedId
                  return (
                    <tr
                      key={account.id}
                      onClick={() => setSelectedId(account.id)}
                      style={{ cursor: 'pointer', background: isActive ? 'rgba(59,130,246,0.06)' : undefined }}
                    >
                      <td>
                        <div style={{ fontWeight: 500 }}>{account.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 3 }}>{account.institution_name ?? 'No institution'}</div>
                      </td>
                      <td><AccountTag type={account.type} /></td>
                      <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{usd(account.balance)}</td>
                      <td><FreshnessDot lastUpdated={account.last_updated} /></td>
                      <td>
                        <ActionsMenu
                          disabled={saving}
                          items={[
                            { label: 'Edit', onClick: () => openAccountEdit(account) },
                            { label: 'Set balance', onClick: () => openBalanceModal(account) },
                            { label: 'Delete', onClick: () => deleteAccount(account), destructive: true },
                          ]}
                        />
                      </td>
                    </tr>
                  )
                })}
                <tr style={{ background: 'var(--bg-elevated)' }}>
                  <td colSpan={2} style={{ fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.6px', color: 'var(--text-3)' }}>Total</td>
                  <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{usd(totalBalance)}</td>
                  <td colSpan={2} />
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="empty">
              <div className="empty-icon">◻</div>
              <div className="empty-title">No accounts yet</div>
              <div className="empty-sub" style={{ marginBottom: 16 }}>Add an account to start manual entry or import data.</div>
              <button className="btn btn-primary" onClick={openAccountCreate}>Add account</button>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 0 }}>
          {!activeAccount ? (
            <div className="empty">
              <div className="empty-icon">◌</div>
              <div className="empty-title">Pick an account</div>
              <div className="empty-sub">Holdings, transactions, balance snapshots, and debt details show up here.</div>
            </div>
          ) : detailLoading ? (
            <div style={{ padding: 24, color: 'var(--text-3)', fontSize: 13 }}>Loading account details…</div>
          ) : (
            <div style={{ padding: 20 }}>
              <div className="flex-between mb-16" style={{ alignItems: 'start' }}>
                <div>
                  <div className="section-label mb-8">Selected account</div>
                  <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 600, lineHeight: 1.05 }}>{activeAccount.name}</div>
                  <div className="flex-center" style={{ flexWrap: 'wrap', marginTop: 10 }}>
                    <AccountTag type={activeAccount.type} />
                    <FreshnessDot lastUpdated={activeAccount.last_updated} />
                    <span style={{ color: 'var(--text-3)', fontSize: 12 }}>{activeAccount.institution_name ?? 'No institution attached'}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="section-label mb-8">Balance</div>
                  <div className="num-large">{usd(activeAccount.balance)}</div>
                  <div style={{ marginTop: 4, color: 'var(--text-3)', fontSize: 12 }}>Updated {activeFreshness.label}</div>
                </div>
              </div>

              <div className="flex gap-8 mb-16" style={{ flexWrap: 'wrap' }}>
                <button className="btn btn-sm" onClick={() => openAccountEdit(activeAccount)}>Edit account</button>
                <button className="btn btn-sm" onClick={() => openBalanceModal(activeAccount)}>Set balance</button>
                <button className="btn btn-sm" onClick={() => deleteAccount(activeAccount)} disabled={saving}>Delete account</button>
              </div>

              <div className="grid-2 mb-16" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                <div style={{ padding: 14, borderRadius: 12, border: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.015)' }}>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>Account type</div>
                  <div style={{ fontWeight: 500 }}>{humanize(activeAccount.type)}</div>
                </div>
                <div style={{ padding: 14, borderRadius: 12, border: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.015)' }}>
                  <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>Created</div>
                  <div style={{ fontWeight: 500 }}>{formatDate(activeAccount.created_at)}</div>
                </div>
              </div>

              {INVESTMENT_TYPES.has(activeAccount.type) && (
                <div className="card" style={{ padding: 14, marginBottom: 16, borderColor: 'rgba(96,165,250,0.2)' }}>
                  <div className="section-label mb-8">Performance baseline (S&P 500)</div>
                  <div className="grid-3" style={{ gap: 12 }}>
                    <div>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4 }}>Account return</div>
                      <div style={{ fontWeight: 600, color: (performance?.gain_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                        {performance?.gain_pct != null ? `${performance.gain_pct >= 0 ? '+' : ''}${performance.gain_pct.toFixed(2)}%` : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4 }}>S&P baseline</div>
                      <div style={{ fontWeight: 600 }}>{performance?.benchmark_gain_pct != null ? `${performance.benchmark_gain_pct.toFixed(2)}%` : '—'}</div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4 }}>Relative</div>
                      <div style={{ fontWeight: 600, color: (performance?.relative_gain_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                        {performance?.relative_gain_pct != null ? `${performance.relative_gain_pct >= 0 ? '+' : ''}${performance.relative_gain_pct.toFixed(2)}%` : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {DEBT_TYPES.has(activeAccount.type) && (
                <div className="card" style={{ padding: 18, marginBottom: 16, borderColor: 'rgba(248,113,113,0.18)' }}>
                  <div className="flex-between mb-8">
                    <div>
                      <div className="section-label mb-8">Debt detail</div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>Keep APR, monthly payment, and payoff timing current for planning.</div>
                    </div>
                    {activeDebt?.months_to_payoff != null && <Badge label={`${activeDebt.months_to_payoff} mo payoff`} tone="red" />}
                  </div>

                  <div className="grid-3" style={{ marginBottom: 14 }}>
                    <div style={{ padding: 12, borderRadius: 12, border: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.015)' }}>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>APR</div>
                      <div style={{ fontWeight: 500 }}>{activeDebt ? percent(activeDebt.interest_rate) : '—'}</div>
                    </div>
                    <div style={{ padding: 12, borderRadius: 12, border: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.015)' }}>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>Minimum payment</div>
                      <div style={{ fontWeight: 500 }}>{activeDebt ? usd(activeDebt.minimum_payment) : '—'}</div>
                    </div>
                    <div style={{ padding: 12, borderRadius: 12, border: '1px solid var(--border-soft)', background: 'rgba(255,255,255,0.015)' }}>
                      <div style={{ color: 'var(--text-3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>Payoff date</div>
                      <div style={{ fontWeight: 500 }}>{activeDebt?.payoff_date ? formatDate(activeDebt.payoff_date) : '—'}</div>
                    </div>
                  </div>

                  <div className="grid-3" style={{ gap: 12 }}>
                    <div className="field" style={{ marginBottom: 0 }}>
                      <label>APR (%)</label>
                      <input value={debtDraft.interest_rate} onChange={(e) => setDebtDraft((draft) => ({ ...draft, interest_rate: e.target.value }))} />
                    </div>
                    <div className="field" style={{ marginBottom: 0 }}>
                      <label>Minimum payment</label>
                      <input type="number" value={debtDraft.minimum_payment} onChange={(e) => setDebtDraft((draft) => ({ ...draft, minimum_payment: e.target.value }))} />
                    </div>
                    <div className="field" style={{ marginBottom: 0 }}>
                      <label>Payoff date</label>
                      <input type="date" value={debtDraft.payoff_date} onChange={(e) => setDebtDraft((draft) => ({ ...draft, payoff_date: e.target.value }))} />
                    </div>
                  </div>

                  <div className="flex-end mt-12">
                    <button className="btn btn-primary" onClick={saveDebt} disabled={saving}>Save debt detail</button>
                  </div>
                </div>
              )}

              {INVESTMENT_TYPES.has(activeAccount.type) && (
                <div className="card" style={{ padding: 18, marginBottom: 16 }}>
                  <div className="flex-between mb-12">
                    <div>
                      <div className="section-label mb-8">Holdings</div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>Track positions, cost basis, and current value for investment accounts.</div>
                    </div>
                    <button className="btn btn-sm btn-primary" onClick={() => openHoldingCreate(activeAccount)}>Add holding</button>
                  </div>

                  {detail?.holdings.length ? (
                    <table className="tbl">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th style={{ textAlign: 'right' }}>Qty</th>
                          <th style={{ textAlign: 'right' }}>Cost basis</th>
                          <th style={{ textAlign: 'right' }}>Last price</th>
                          <th style={{ textAlign: 'right' }}>Market value</th>
                          <th style={{ textAlign: 'right' }}>Gain/loss</th>
                          <th style={{ textAlign: 'right' }}>% of acct</th>
                          <th>Freshness</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...detail.holdings].sort((a, b) => b.market_value - a.market_value).map((holding) => {
                          const costBasis = holding.cost_basis ?? null
                          const gain = costBasis == null ? null : holding.market_value - costBasis
                          const gainPct = costBasis && costBasis !== 0 ? (gain! / costBasis) * 100 : null
                          const weight = holdingsTotal > 0 ? (holding.market_value / holdingsTotal) * 100 : null
                          return (
                            <tr key={holding.id}>
                              <td style={{ fontWeight: 500 }}>{holding.symbol}</td>
                              <td className="num" style={{ textAlign: 'right' }}>{qty(holding.quantity)}</td>
                              <td className="num" style={{ textAlign: 'right' }}>{costBasis == null ? '—' : usd(costBasis)}</td>
                              <td className="num" style={{ textAlign: 'right' }}>{holding.last_price == null ? '—' : usd(holding.last_price)}</td>
                              <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{usd(holding.market_value)}</td>
                              <td className="num" style={{ textAlign: 'right', color: gain != null ? (gain >= 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-3)' }}>
                                {gain == null ? '—' : `${gain >= 0 ? '+' : ''}${usd(gain)}`}
                              </td>
                              <td className="num" style={{ textAlign: 'right' }}>{weight == null ? '—' : `${weight.toFixed(1)}%`}</td>
                              <td><FreshnessDot lastUpdated={holding.last_updated} /></td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <div className="empty" style={{ padding: '28px 20px 12px' }}>
                      <div className="empty-title">No holdings yet</div>
                      <div className="empty-sub" style={{ marginBottom: 12 }}>Add your first position to start tracking cost basis and market value.</div>
                      <button className="btn btn-primary" onClick={() => openHoldingCreate(activeAccount)}>Add holding</button>
                    </div>
                  )}
                </div>
              )}

              {activeAccount.type === 'real_estate' && (
                <div className="card" style={{ padding: 18, marginBottom: 16 }}>
                  <div className="flex-between mb-12">
                    <div>
                      <div className="section-label mb-8">Real estate details</div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.5 }}>
                        Value, mortgage, LTV, and equity are shown per property in this account.
                      </div>
                    </div>
                    <a className="btn btn-sm" href="/real-estate">Open Real Estate page</a>
                  </div>
                  {activeProperties.length > 0 ? (
                    <table className="tbl">
                      <thead>
                        <tr>
                          <th>Address</th>
                          <th style={{ textAlign: 'right' }}>Value</th>
                          <th style={{ textAlign: 'right' }}>Mortgage</th>
                          <th style={{ textAlign: 'right' }}>LTV</th>
                          <th style={{ textAlign: 'right' }}>Equity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeProperties.map((property) => (
                          <tr key={property.id}>
                            <td style={{ maxWidth: 280 }}>{property.address}</td>
                            <td className="num" style={{ textAlign: 'right' }}>{usd(property.effective_value)}</td>
                            <td className="num" style={{ textAlign: 'right' }}>{usd(property.mortgage_balance)}</td>
                            <td className="num" style={{ textAlign: 'right' }}>{property.ltv == null ? '—' : `${property.ltv.toFixed(1)}%`}</td>
                            <td className="num" style={{ textAlign: 'right', color: 'var(--green)', fontWeight: 600 }}>{usd(property.equity)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="empty" style={{ padding: '20px 12px' }}>
                      <div className="empty-title">No properties on this account</div>
                      <div className="empty-sub">Add one in the Real Estate page to track value and equity.</div>
                    </div>
                  )}
                </div>
              )}

              <div className="card" style={{ padding: 18 }}>
                <div className="flex-between mb-12">
                  <div>
                    <div className="section-label mb-8">Transactions</div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>
                      Search and filter by date, type, and amount. Imported rows are read-only.
                    </div>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => openTransactionCreate(activeAccount)}>Add transaction</button>
                </div>

                <div className="grid-3 mb-16" style={{ gap: 10 }}>
                  <input placeholder="Search symbol/description" value={txSearch} onChange={(e) => setTxSearch(e.target.value)} />
                  <select value={txTypeFilter} onChange={(e) => setTxTypeFilter(e.target.value)}>
                    <option value="">All types</option>
                    {TRANSACTION_TYPES.map((type) => (
                      <option key={type} value={type}>{humanize(type)}</option>
                    ))}
                  </select>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <input type="number" placeholder="Min amount" value={txMinAmount} onChange={(e) => setTxMinAmount(e.target.value)} />
                    <input type="number" placeholder="Max amount" value={txMaxAmount} onChange={(e) => setTxMaxAmount(e.target.value)} />
                  </div>
                  <input type="date" value={txFromDate} onChange={(e) => setTxFromDate(e.target.value)} />
                  <input type="date" value={txToDate} onChange={(e) => setTxToDate(e.target.value)} />
                  <button
                    className="btn btn-sm"
                    onClick={() => {
                      setTxSearch('')
                      setTxTypeFilter('')
                      setTxMinAmount('')
                      setTxMaxAmount('')
                      setTxFromDate('')
                      setTxToDate('')
                    }}
                  >
                    Clear filters
                  </button>
                </div>

                {(transactions ?? []).length > 0 ? (
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Symbol</th>
                        <th style={{ textAlign: 'right' }}>Qty</th>
                        <th style={{ textAlign: 'right' }}>Price</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                        <th>Description</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...(transactions ?? [])].sort((a, b) => b.date.localeCompare(a.date)).map((txn) => (
                        <tr key={txn.id}>
                          <td>{formatDate(txn.date)}</td>
                          <td>
                            <Badge
                              label={humanize(txn.type)}
                              tone={isImportedTransaction(txn) ? 'blue' : 'neutral'}
                              title={isImportedTransaction(txn) ? 'Imported row' : 'Manual row'}
                            />
                          </td>
                          <td style={{ fontWeight: 500 }}>{txn.symbol ?? '—'}</td>
                          <td className="num" style={{ textAlign: 'right' }}>{qty(txn.quantity)}</td>
                          <td className="num" style={{ textAlign: 'right' }}>{txn.price == null ? '—' : usd(txn.price)}</td>
                          <td className="num" style={{ textAlign: 'right', fontWeight: 500 }}>{txn.amount == null ? '—' : usd(txn.amount)}</td>
                          <td style={{ color: 'var(--text-2)', maxWidth: 220 }}>{txn.description ?? '—'}</td>
                          <td>
                            {isImportedTransaction(txn) ? (
                              <span style={{ color: 'var(--text-3)', fontSize: 12 }}>locked</span>
                            ) : (
                              <ActionsMenu
                                disabled={saving}
                                items={[
                                  { label: 'Edit', onClick: () => openTransactionEdit(activeAccount, txn) },
                                  { label: 'Delete', onClick: () => deleteTransaction(activeAccount, txn), destructive: true },
                                ]}
                              />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="empty" style={{ padding: '24px 20px 8px' }}>
                    <div className="empty-title">No matching transactions</div>
                    <div className="empty-sub" style={{ marginBottom: 12 }}>Try broadening filters or create a manual transaction.</div>
                    <button className="btn btn-primary" onClick={() => openTransactionCreate(activeAccount)}>Add transaction</button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {modal?.kind === 'account' && (
        <ModalShell
          title={modal.mode === 'create' ? 'Add account' : `Edit ${modal.account.name}`}
          subtitle="Create the account container first. You can then attach balance, transactions, and holdings from this page."
          onClose={closeModal}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void saveAccount()
            }}
          >
            <div className="grid-2">
              <div className="field">
                <label>Name</label>
                <input value={accountDraft.name} onChange={(e) => setAccountDraft((draft) => ({ ...draft, name: e.target.value }))} placeholder="Fidelity Roth IRA" />
              </div>
              <div className="field">
                <label>Type</label>
                <select value={accountDraft.type} onChange={(e) => setAccountDraft((draft) => ({ ...draft, type: e.target.value as AccountType }))}>
                  {ACCOUNT_TYPES.map((type) => (
                    <option key={type} value={type}>{humanize(type)}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Institution ID</label>
                <input value={accountDraft.institution_id} onChange={(e) => setAccountDraft((draft) => ({ ...draft, institution_id: e.target.value }))} placeholder="Leave blank for none" />
              </div>
              <div className="field">
                <label>Currency</label>
                <input value={accountDraft.currency} onChange={(e) => setAccountDraft((draft) => ({ ...draft, currency: e.target.value }))} placeholder="USD" />
              </div>
            </div>
            <div className="flex-end gap-8">
              {modal.mode === 'edit' && <button type="button" className="btn" onClick={() => deleteAccount(modal.account)} disabled={saving}>Delete</button>}
              <button type="button" className="btn" onClick={closeModal}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving || !accountDraft.name.trim()}>Save account</button>
            </div>
          </form>
        </ModalShell>
      )}

      {modal?.kind === 'balance' && (
        <ModalShell
          title={`Set balance for ${modal.account.name}`}
          subtitle="Use this when the account balance is known directly and you want the current snapshot corrected."
          onClose={closeModal}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void saveBalance()
            }}
          >
            <div className="grid-2">
              <div className="field">
                <label>Balance</label>
                <input type="number" value={balanceDraft.balance} onChange={(e) => setBalanceDraft((draft) => ({ ...draft, balance: e.target.value }))} />
              </div>
              <div className="field">
                <label>Effective date</label>
                <input type="date" value={balanceDraft.date} onChange={(e) => setBalanceDraft((draft) => ({ ...draft, date: e.target.value }))} />
              </div>
            </div>
            <div className="flex-end gap-8">
              <button type="button" className="btn" onClick={closeModal}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving || toNumber(balanceDraft.balance) == null}>Save balance</button>
            </div>
          </form>
        </ModalShell>
      )}

      {modal?.kind === 'transaction' && (
        <ModalShell
          title={modal.mode === 'create' ? `Add transaction to ${modal.account.name}` : 'Edit transaction'}
          subtitle="Manual transactions are handy for adjustments, cash movements, and entries that should not come from an import file."
          onClose={closeModal}
          width={820}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void saveTransaction()
            }}
          >
            <div className="grid-3">
              <div className="field">
                <label>Date</label>
                <input type="date" value={transactionDraft.date} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, date: e.target.value }))} />
              </div>
              <div className="field">
                <label>Type</label>
                <select value={transactionDraft.type} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, type: e.target.value }))}>
                  {TRANSACTION_TYPES.map((type) => (
                    <option key={type} value={type}>{humanize(type)}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Symbol</label>
                <input value={transactionDraft.symbol} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, symbol: e.target.value }))} placeholder="AAPL or cash" />
              </div>
              <div className="field">
                <label>Quantity</label>
                <input type="number" step="0.0001" value={transactionDraft.quantity} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, quantity: e.target.value }))} />
              </div>
              <div className="field">
                <label>Price</label>
                <input type="number" step="0.01" value={transactionDraft.price} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, price: e.target.value }))} />
              </div>
              <div className="field">
                <label>Amount</label>
                <input type="number" step="0.01" value={transactionDraft.amount} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, amount: e.target.value }))} />
              </div>
            </div>
            <div className="field">
              <label>Description</label>
              <input value={transactionDraft.description} onChange={(e) => setTransactionDraft((draft) => ({ ...draft, description: e.target.value }))} placeholder="Transfer, dividend, fee, and so on" />
            </div>
            <div className="flex-end gap-8">
              <button type="button" className="btn" onClick={closeModal}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>Save transaction</button>
            </div>
          </form>
        </ModalShell>
      )}

      {modal?.kind === 'holding' && (
        <ModalShell
          title={modal.mode === 'create' ? `Add holding to ${modal.account.name}` : 'Edit holding'}
          subtitle="Use this for manual position management on investment accounts."
          onClose={closeModal}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void saveHolding()
            }}
          >
            <div className="grid-2">
              <div className="field">
                <label>Symbol</label>
                <input value={holdingDraft.symbol} onChange={(e) => setHoldingDraft((draft) => ({ ...draft, symbol: e.target.value }))} placeholder="VTI" />
              </div>
              <div className="field">
                <label>Quantity</label>
                <input type="number" step="0.0001" value={holdingDraft.quantity} onChange={(e) => setHoldingDraft((draft) => ({ ...draft, quantity: e.target.value }))} />
              </div>
              <div className="field">
                <label>Cost basis</label>
                <input type="number" step="0.01" value={holdingDraft.cost_basis} onChange={(e) => setHoldingDraft((draft) => ({ ...draft, cost_basis: e.target.value }))} />
              </div>
              <div className="field">
                <label>Last price</label>
                <input type="number" step="0.01" value={holdingDraft.last_price} onChange={(e) => setHoldingDraft((draft) => ({ ...draft, last_price: e.target.value }))} />
              </div>
            </div>
            <div className="flex-end gap-8">
              <button type="button" className="btn" onClick={closeModal}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving || !holdingDraft.symbol.trim() || toNumber(holdingDraft.quantity) == null}>Save holding</button>
            </div>
          </form>
        </ModalShell>
      )}
    </div>
  )
}
