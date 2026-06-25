export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface KnowledgeDocumentItem {
  id: string
  title: string
  filename: string
  mimeType: string
  fileSize: number
  status: DocumentStatus
  chunkCount: number
  errorMessage?: string | null
  uploadedBy: string
  createdAt?: string | null
  updatedAt?: string | null
}

export interface KnowledgeChunkItem {
  chunkIndex: number
  content: string
  tokenCount: number
}

export interface KnowledgeSearchHit {
  content: string
  title: string
  score: number
  documentId: string
  chunkIndex: number
}

export interface KnowledgeSearchResult {
  results: KnowledgeSearchHit[]
  query: string
  totalTokens: number
}

export const DOCUMENT_STATUS_MAP: Record<
  DocumentStatus,
  { label: string; color: string }
> = {
  pending: { label: '待处理', color: 'default' },
  processing: { label: '处理中', color: 'processing' },
  ready: { label: '就绪', color: 'success' },
  failed: { label: '失败', color: 'error' },
}
