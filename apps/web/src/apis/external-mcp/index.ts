import { serverApi, type Response } from '..';
import type { ExternalMcpTemplateItem, UpsertExternalMcpBody } from '@en/common/external-mcp';

export const listExternalMcp = (): Promise<Response<ExternalMcpTemplateItem[]>> => {
    return serverApi.get('/user/external-mcp') as Promise<Response<ExternalMcpTemplateItem[]>>;
};

export const upsertExternalMcp = (
    alias: string,
    body: UpsertExternalMcpBody,
): Promise<Response<ExternalMcpTemplateItem>> => {
    return serverApi.put(`/user/external-mcp/${alias}`, body) as Promise<Response<ExternalMcpTemplateItem>>;
};

export const testExternalMcp = (alias: string): Promise<Response<{ tools: unknown[] }>> => {
    return serverApi.post(`/user/external-mcp/${alias}/test`) as Promise<Response<{ tools: unknown[] }>>;
};

export const deleteExternalMcp = (alias: string): Promise<Response<{ deleted: boolean }>> => {
    return serverApi.delete(`/user/external-mcp/${alias}`) as Promise<Response<{ deleted: boolean }>>;
};
