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
  description: string
  why: string
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
