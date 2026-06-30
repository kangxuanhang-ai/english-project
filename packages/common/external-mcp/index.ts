export interface ExternalMcpHeaderField {
  key: string
  label: string
  required: boolean
  secret: boolean
  placeholder?: string
}

export interface ExternalMcpConnectionState {
  enabled: boolean
  configuredHeaders: Record<string, boolean>
  lastTestedAt: string | null
  toolNames: string[]
  needsTest?: boolean
}

export interface ExternalMcpTemplateItem {
  alias: string
  displayName: string
  description: string
  globallyEnabled: boolean
  headerSchema: { fields: ExternalMcpHeaderField[] }
  exposedToolNames: string[]
  connection?: ExternalMcpConnectionState
}

export interface AdminMcpTemplateItem {
  id: string
  alias: string
  displayName: string
  description: string
  url: string
  headerSchema: { fields: ExternalMcpHeaderField[] }
  globallyEnabled: boolean
  enabledRoles: string[]
  toolsCache: Array<{ name: string; description?: string }> | null
  exposedTools: string[] | null
  exposedToolNames: string[]
  fetchUrlAllowlist: string[] | null
  lastSyncedAt: string | null
  sortOrder: number
}

export interface UpsertExternalMcpBody {
  enabled: boolean
  headers?: Record<string, string>
}
