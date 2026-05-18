import { api } from './client'

export interface OFXConnection {
  id: number
  name: string
  provider: string
  status: 'active' | 'error' | 'disabled'
  account_id: number | null
  fi_id: string
  org: string
  account_number: string
  account_type: string
  is_investment: boolean
  last_sync_at: string | null
  last_error: string | null
  last_run: {
    status: string
    trigger: string
    started_at: string | null
    finished_at: string | null
    details: Record<string, unknown> | null
  } | null
}

export interface OFXConnectionCreate {
  name: string
  url: string
  fi_id: string
  org: string
  account_number: string
  account_type: string
  is_investment: boolean
  broker_id: string | null
  account_id: number
  username: string
  password: string
}

export interface OFXSyncResult {
  synced?: number
  errors?: Array<{ connection_id: number; name: string; error: string }>
  results?: Array<Record<string, unknown>>
  status?: string
  imported?: number
  skipped?: number
}

export const ofxApi = {
  listConnections: () => api.get<OFXConnection[]>('/ofx/connections'),
  addConnection: (body: OFXConnectionCreate) => api.post<OFXConnection>('/ofx/connections', body),
  deleteConnection: (id: number) => api.delete<{ ok: boolean }>(`/ofx/connections/${id}`),
  syncAll: () => api.post<OFXSyncResult>('/ofx/sync'),
  syncOne: (connectionId: number) => api.post<OFXSyncResult>('/ofx/sync', { connection_id: connectionId }),
}

export const KNOWN_INSTITUTIONS: Record<string, Partial<OFXConnectionCreate>> = {
  fidelity: {
    url: 'https://ofx.fidelity.com/ftgw/OFX/clients/download',
    fi_id: '7776',
    org: 'fidelity.com',
    account_type: 'INDIVIDUAL',
    is_investment: true,
    broker_id: 'fidelity.com',
  },
  custom: {
    url: '',
    fi_id: '',
    org: '',
    account_type: 'CHECKING',
    is_investment: false,
    broker_id: null,
  },
}
