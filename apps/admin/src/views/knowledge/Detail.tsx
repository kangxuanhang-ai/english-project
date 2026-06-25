import { Button, Col, Descriptions, Row, Space, Table, Tag, Typography, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  fetchKnowledgeChunks,
  fetchKnowledgeDoc,
  fetchKnowledgeDownloadUrl,
} from '@/apis/admin'
import { DataCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import type { KnowledgeChunkItem, DocumentStatus } from '@en/common/knowledge'
import { DOCUMENT_STATUS_MAP } from '@en/common/knowledge'

export default function KnowledgeDetailPage() {
  const { id = '' } = useParams()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const { data: docRes, isLoading: docLoading } = useQuery({
    queryKey: ['admin-knowledge-doc', id],
    queryFn: () => fetchKnowledgeDoc(id),
    enabled: !!id,
  })

  const { data: chunksRes, isLoading: chunksLoading } = useQuery({
    queryKey: ['admin-knowledge-chunks', id, page, pageSize],
    queryFn: () => fetchKnowledgeChunks(id, { page, pageSize }),
    enabled: !!id,
  })

  const doc = docRes?.data
  const statusMeta = doc ? DOCUMENT_STATUS_MAP[doc.status as DocumentStatus] : null

  const handleDownload = async () => {
    try {
      const res = await fetchKnowledgeDownloadUrl(id)
      window.open(res.data.url, '_blank')
    } catch {
      message.error('获取下载链接失败')
    }
  }

  const columns = [
    { title: '序号', dataIndex: 'chunkIndex', key: 'chunkIndex', width: 80 },
    { title: 'Token', dataIndex: 'tokenCount', key: 'tokenCount', width: 90 },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (v: string) => (
        <Typography.Paragraph ellipsis={{ rows: 3, expandable: true }} style={{ margin: 0 }}>
          {v}
        </Typography.Paragraph>
      ),
    },
  ]

  return (
    <PageShell
      title={doc?.title ?? '文档详情'}
      back
      extra={
        statusMeta ? <Tag color={statusMeta.color}>{statusMeta.label}</Tag> : undefined
      }
    >
      <Row gutter={16}>
        <Col xs={24} lg={16}>
          <DataCard loading={docLoading}>
            <Descriptions
              bordered
              column={2}
              size="small"
              labelStyle={{ width: 120, background: '#fafafa' }}
            >
              <Descriptions.Item label="标题">{doc?.title ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="文件名">{doc?.filename ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {statusMeta ? (
                  <Tag color={statusMeta.color}>{statusMeta.label}</Tag>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="分块数">{doc?.chunkCount ?? 0}</Descriptions.Item>
              <Descriptions.Item label="文件大小">
                {doc ? `${(doc.fileSize / 1024).toFixed(1)} KB` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="上传时间">
                {formatDateTime(doc?.createdAt)}
              </Descriptions.Item>
              {doc?.errorMessage ? (
                <Descriptions.Item label="错误信息" span={2}>
                  <Typography.Text type="danger">{doc.errorMessage}</Typography.Text>
                </Descriptions.Item>
              ) : null}
            </Descriptions>
            <Space style={{ marginTop: 16 }}>
              <Button onClick={handleDownload} disabled={!doc}>
                下载原件
              </Button>
            </Space>
          </DataCard>
        </Col>
        <Col xs={24} lg={8}>
          <DataCard title="分块预览">
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              共 {doc?.chunkCount ?? 0} 个分块，下方表格可浏览全部内容
            </Typography.Text>
          </DataCard>
        </Col>
      </Row>

      <div style={{ marginTop: 16 }}>
        <DataCard title="分块内容" flush>
        <Table<KnowledgeChunkItem>
          rowKey="chunkIndex"
          size="middle"
          loading={docLoading || chunksLoading}
          columns={columns}
          dataSource={chunksRes?.data.list ?? []}
          pagination={{
            current: page,
            pageSize,
            total: chunksRes?.data.total ?? 0,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </DataCard>
      </div>
    </PageShell>
  )
}
