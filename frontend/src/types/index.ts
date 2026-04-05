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
}

export interface AccountDetail extends Account {
  holdings: Holding[]
}

export type AccountType =
  | 'brokerage'
  | 'crypto'
  | 'real_estate'
  | 'savings'
  | 'hsa'
  | 'roth_ira'
  | '401k'
  | 'checking'
  | 'credit_card'
  | 'student_loan'
  | 'auto_loan'
  | 'personal_loan'

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
  account_id: number
  date: string
  type: string
  symbol: string | null
  quantity: number | null
  price: number | null
  amount: number | null
  description: string | null
}

export interface BalanceSnapshot {
  date: string
  net_worth: number
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

export interface NetWorth {
  net_worth: number
  previous: number
  delta: number
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
  status: string
  error_message: string | null
  created_at: string | null
}
