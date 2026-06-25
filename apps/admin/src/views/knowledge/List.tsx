import {
  Button,
  Card,
  Input,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Upload,
  message,
} from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  deleteKnowledgeDoc,
  fetchKnowledgeDocs,
  reindexKnowledgeDoc,
  uploadKnowledgeFile,
} from '@/apis/admin'
import { DataCard, FilterCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import type { KnowledgeDocumentItem } from '@en/common/knowledge'
import { DOCUMENT_STATUS_MAP } from '@en/common/knowledge'

const { Dragger } = Upload

export default function KnowledgeListPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    const s = searchParams.get('status')
    if (s) {
      setStatus(s)
      setPage(1)
    }
  }, [searchParams])

  const { data, isLoading } = useQuery({
    queryKey: ['admin-knowledge', page, pageSize, keyword, status],
    queryFn: () =>
      fetchKnowledgeDocs({
        page,
        pageSize,
        keyword: keyword || undefined,
        status: status || undefined,
      }),
    refetchInterval: (query) => {
      const list = query.state.data?.data.list ?? []
      const busy = list.some((d) => d.status === 'pending' || d.status === 'processing')
      return busy ? 3000 : false
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteKnowledgeDoc(id),
    onSuccess: () => {
      message.success('已删除')
      queryClient.invalidateQueries({ queryKey: ['admin-knowledge'] })
    },
    onError: () => message.error('删除失败'),
  })

  const reindexMut = useMutation({
    mutationFn: (id: string) => reindexKnowledgeDoc(id),
    onSuccess: () => {
      message.success('已开始重新索引')
      queryClient.invalidateQueries({ queryKey: ['admin-knowledge'] })
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      message.error(err.response?.data?.message ?? '重新索引失败')
    },
  })

  const uploadQueue = useMemo(() => ({ running: false }), [])

  const handleUpload = async (file: File) => {
    if (uploadQueue.running) {
      await new Promise((r) => setTimeout(r, 300))
    }
    uploadQueue.running = true
    try {
      await uploadKnowledgeFile(file)
      message.success(`${file.name} 上传成功`)
      queryClient.invalidateQueries({ queryKey: ['admin-knowledge'] })
    } catch {
      message.error(`${file.name} 上传失败`)
    } finally {
      uploadQueue.running = false
    }
    return false
  }

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '文件名', dataIndex: 'filename', key: 'filename', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: KnowledgeDocumentItem['status'], record: KnowledgeDocumentItem) => {
        const meta = DOCUMENT_STATUS_MAP[v]
        if (v === 'pending' || v === 'processing') {
          return (
            <Space>
              <Tag color={meta.color}>{meta.label}</Tag>
              <Progress percent={undefined} size="small" style={{ width: 72 }} status="active" />
            </Space>
          )
        }
        if (v === 'failed' && record.errorMessage) {
          return (
            <Tooltip title={record.errorMessage.slice(0, 120)}>
              <Tag color="error">{meta.label}</Tag>
            </Tooltip>
          )
        }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    { title: '分块数', dataIndex: 'chunkCount', key: 'chunkCount', width: 90 },
    {
      title: '上传时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (v: string | null | undefined) => formatDateTime(v),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, record: KnowledgeDocumentItem) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/knowledge/${record.id}`)}>
            详情
          </Button>
          <Button
            type="link"
            disabled={record.status === 'processing' || record.status === 'pending'}
            onClick={() => reindexMut.mutate(record.id)}
          >
            重建索引
          </Button>
          <Popconfirm title="确认删除该文档？" onConfirm={() => deleteMut.mutate(record.id)}>
            <Button type="link" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <PageShell title="知识库" description="上传文档并向量化，供 AI 检索使用">
      <FilterCard>
        <Space wrap>
          <Input.Search
            placeholder="搜索标题"
            allowClear
            onSearch={(v) => {
              setKeyword(v)
              setPage(1)
            }}
            style={{ width: 220 }}
          />
          <Select
            allowClear
            placeholder="文档状态"
            style={{ width: 140 }}
            value={status}
            onChange={(v) => {
              setStatus(v)
              setPage(1)
              if (v) setSearchParams({ status: v })
              else setSearchParams({})
            }}
            options={Object.entries(DOCUMENT_STATUS_MAP).map(([value, { label }]) => ({
              value,
              label,
            }))}
          />
          <Button onClick={() => navigate('/knowledge/search')}>检索测试</Button>
        </Space>
      </FilterCard>

      <Card
        bordered={false}
        className="admin-upload-dragger"
        style={{ marginBottom: 16, boxShadow: 'var(--admin-shadow-card)' }}
        styles={{ body: { padding: 24 } }}
      >
        <Dragger
          multiple
          showUploadList={false}
          accept=".txt,.md,.pdf,.docx"
          beforeUpload={(file) => {
            void handleUpload(file as File)
            return false
          }}
        >
          <p className="ant-upload-text">点击或拖拽上传知识库文档</p>
          <p className="ant-upload-hint">支持 .txt / .md / .pdf / .docx，单文件最大 20MB</p>
        </Dragger>
      </Card>

      <DataCard flush>
        <Table<KnowledgeDocumentItem>
          rowKey="id"
          size="middle"
          loading={isLoading}
          columns={columns}
          dataSource={data?.data.list ?? []}
          pagination={{
            current: page,
            pageSize,
            total: data?.data.total ?? 0,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </DataCard>
    </PageShell>
  )
}
