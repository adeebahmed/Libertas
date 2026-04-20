export interface Institution {
  id: number
  name: string
  export_url: string | null
  file_pattern: string | null
  column_mapping: Record<string, string> | null
  importer_preset: string
  notes: string | null
}

export interface Account {
  id: number
  name: string
  type: AccountType
  institution_id: number | null
  institution_name: string | null
  currency: string
  created_at: string | null
  balance: number
  last_updated: string | null
  sync_source?: string | null
  source_kind?: string | null
  source_record_id?: string | null
  source_priority?: number | null
  provenance?: Record<string, unknown> | null
  merge_conflict?: boolean
}

export interface AccountDetail extends Account {
  holdings: Holding[]
}

export type AccountType =
  | 'brokerage'
  | 'crypto'
  | 'savings'
  | 'hsa'
  | 'roth_ira'
  | '401k'
  | 'checking'
  | 'credit_card'
  | 'student_loan'
  | 'auto_loan'
  | 'personal_loan'
  | 'real_estate'
  | 'mortgage'
  | 'other'

export interface Holding {
  id: number
  symbol: string
  quantity: number
  cost_basis: number | null
  last_price: number | null
  last_updated: string | null
  market_value: number
}

export interface Transaction {
  id: number
  account_id?: number
  date: string
  type: string
  symbol: string | null
  quantity: number | null
  price: number | null
  amount: number | null
  description: string | null
  import_log_id?: number | null
  import_hash?: string | null
  sync_source?: string | null
  source_kind?: string | null
  source_record_id?: string | null
  source_priority?: number | null
  canonical_key?: string | null
  provenance?: Record<string, unknown> | null
  merge_conflict?: boolean
}

export interface IntegrationRun {
  status: string
  trigger: string
  started_at: string | null
  finished_at: string | null
  details: Record<string, unknown> | null
}

export interface IntegrationConnection {
  id: number
  provider: 'plaid' | 'sheets'
  name: string
  status: string
  config: Record<string, unknown> | null
  external_item_id: string | null
  last_sync_at: string | null
  last_error: string | null
  last_run: IntegrationRun | null
}

export interface BalanceSnapshot {
  date: string
  net_worth: number
}

export interface AccountPerformance {
  snapshots: { date: string; balance: number }[]
  gain_pct: number | null
  benchmark_gain_pct: number | null
  relative_gain_pct: number | null
  first_balance?: number
  last_balance?: number
}

export interface Property {
  id: number
  account_id: number
  address: string
  purchase_price: number | null
  purchase_date: string | null
  zillow_estimate: number | null
  manual_override: number | null
  effective_value: number | null
  mortgage_balance: number | null
  mortgage_rate: number | null
  equity: number
  ltv: number | null
  last_updated: string | null
}

export interface Projection {
  current_balance: number
  params: {
    monthly_contribution: number
    years: number
    conservative_rate: number
    moderate_rate: number
    aggressive_rate: number
  }
  scenarios: {
    conservative: ProjectionPoint[]
    moderate: ProjectionPoint[]
    aggressive: ProjectionPoint[]
  }
}

export interface ProjectionPoint {
  year: number
  value: number
}

export interface Insight {
  title: string
  category: string
  priority: 'high' | 'medium' | 'low'
  action: string
  description: string
  why: string
  icon?: string
  institution_hint?: string | null
}

export interface RetirementPlan {
  current_balance: number
  target: number
  monthly_contribution: number
  years_to_target: number | null
  needed_monthly_contribution: number | null
  on_track: {
    projected_at_retirement: number
    target: number
    on_track: boolean
    shortfall: number
    surplus: number
    years_to_retire: number
  } | null
  scenarios: {
    conservative: { year: number; value: number }[]
    moderate: { year: number; value: number }[]
    aggressive: { year: number; value: number }[]
  }
  settings: {
    birth_year: number | null
    retirement_age: number
    monthly_expenses: number
  }
}

export interface TaxEstimate {
  income_w2: number
  income_1099: number
  total_income: number
  filing_status: string
  agi: number
  standard_deduction: number
  taxable_income: number
  ordinary_tax: number
  self_employment_tax: number
  net_capital_gains: number
  ltcg_tax: number
  total_estimated_tax: number
  effective_rate: number
  quarterly_payment: number
}

export interface TaxHarvestOpportunity {
  symbol: string
  account: string
  quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_loss: number
  loss_pct: number
}

export interface NewsArticle {
  id: number
  source: string
  title: string
  url: string | null
  published_at: string | null
  summary: string | null
  category: string | null
}

export type MarketTapeTone = 'positive' | 'neutral' | 'negative'
export type MarketTapeKind = 'news' | 'ticker' | 'personal'

export interface DashboardTapeNewsItem {
  id: string
  label: string
  url: string
  source: string | null
  published_at: string | null
}

export interface DashboardTapeTickerItem {
  id: string
  symbol: string
  price: number | null
  market_value: number
  portfolio_weight_pct: number
  performance_pct: number | null
  last_updated: string | null
}

export interface DashboardTapePersonalItem {
  id: string
  label: string
  tone: MarketTapeTone
  route: '/accounts' | '/insights'
}

export interface DashboardTapeSequenceItem {
  kind: MarketTapeKind
  ref_id: string
}

export interface DashboardTape {
  generated_at: string
  segments: {
    news: DashboardTapeNewsItem[]
    tickers: DashboardTapeTickerItem[]
    personal: DashboardTapePersonalItem[]
  }
  sequence: DashboardTapeSequenceItem[]
}

export interface NetWorth {
  net_worth: number
  previous: number
  delta: number
  delta_30d?: number | null
  delta_30d_pct?: number | null
  last_updated?: string | null
  by_type: Record<string, number>
}

export interface PendingFile {
  path: string
  filename: string
  institution_id: number | null
  institution_name: string | null
  detected_at: number
}

export interface ImportPreview {
  headers: string[]
  sample_rows: Record<string, string>[]
  suggested_mapping: Record<string, string>
}

export interface DebtAccount {
  account_id: number
  name: string
  type: string
  balance: number
  interest_rate: number
  minimum_payment: number
  payoff_date: string | null
  months_to_payoff: number | null
  total_interest: number | null
  last_updated: string | null
}

export interface DebtSummary {
  total_balance: number
  total_minimum_payment: number
  highest_rate: number
  total_interest_if_minimums: number
}

export interface DebtResponse {
  debts: DebtAccount[]
  summary: DebtSummary
}

export interface ImportLog {
  id: number
  filename: string
  institution_name: string | null
  account_id: number | null
  rows_imported: number
  rows_skipped: number
  rows_failed?: number | null
  parse_errors?: number | null
  potential_transfers?: number | null
  status: string
  error_message: string | null
  created_at: string | null
}
