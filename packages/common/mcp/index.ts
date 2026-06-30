export interface McpApiKeyItem {
    id: string;
    name: string;
    keyPrefix: string;
    createdAt: string | null;
    lastUsedAt: string | null;
}

export interface CreateMcpKeyDto {
    name?: string;
}

export interface CreateMcpKeyResult {
    id: string;
    key: string;
    keyPrefix: string;
    name: string;
    claudeConfig: Record<string, unknown>;
    createdAt: string | null;
}
