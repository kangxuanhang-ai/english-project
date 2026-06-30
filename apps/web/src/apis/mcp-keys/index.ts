import { serverApi, type Response } from '..';
import type { CreateMcpKeyDto, CreateMcpKeyResult, McpApiKeyItem } from '@en/common/mcp';

export const listMcpKeys = (): Promise<Response<McpApiKeyItem[]>> => {
    return serverApi.get('/user/mcp-keys') as Promise<Response<McpApiKeyItem[]>>;
};

export const createMcpKey = (data: CreateMcpKeyDto): Promise<Response<CreateMcpKeyResult>> => {
    return serverApi.post('/user/mcp-keys', data) as Promise<Response<CreateMcpKeyResult>>;
};

export const revokeMcpKey = (keyId: string): Promise<Response<{ revoked: boolean }>> => {
    return serverApi.delete(`/user/mcp-keys/${keyId}`) as Promise<Response<{ revoked: boolean }>>;
};
