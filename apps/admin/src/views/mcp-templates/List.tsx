import {
  Button,
  Drawer,
  Form,
  Input,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { fetchMcpTemplates, testMcpTemplate, updateMcpTemplate } from '@/apis/admin'
import { DataCard, PageShell } from '@/components'
import type { AdminMcpTemplateItem } from '@en/common/external-mcp'

export default function McpTemplatesPage() {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<AdminMcpTemplateItem | null>(null)
  const [form] = Form.useForm()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-mcp-templates'],
    queryFn: fetchMcpTemplates,
  })

  const list = data?.data ?? []

  const saveMut = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      updateMcpTemplate(editing!.id, {
        url: values.url as string,
        description: values.description as string,
        globallyEnabled: values.globallyEnabled as boolean,
        exposedTools: values.exposedTools as string[],
        fetchUrlAllowlist:
          editing?.alias === 'fetch' && typeof values.fetchUrlAllowlist === 'string'
            ? (values.fetchUrlAllowlist as string)
                .split('\n')
                .map((s) => s.trim())
                .filter(Boolean)
            : undefined,
      }),
    onSuccess: () => {
      message.success('已保存')
      queryClient.invalidateQueries({ queryKey: ['admin-mcp-templates'] })
      setEditing(null)
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      message.error(err.response?.data?.message ?? '保存失败')
    },
  })

  const testMut = useMutation({
    mutationFn: (id: string) => testMcpTemplate(id),
    onSuccess: (res) => {
      message.success(`连接成功，发现 ${res.data.tools.length} 个工具`)
      queryClient.invalidateQueries({ queryKey: ['admin-mcp-templates'] })
      if (editing && res.data.template) {
        setEditing(res.data.template)
        form.setFieldsValue({
          exposedTools: res.data.template.exposedTools ?? res.data.template.exposedToolNames,
        })
      }
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      message.error(err.response?.data?.message ?? '测试连接失败')
    },
  })

  const toolOptions = useMemo(() => {
    const cache = editing?.toolsCache ?? []
    return cache.map((t) => ({ label: t.name, value: t.name }))
  }, [editing])

  const openEdit = (row: AdminMcpTemplateItem) => {
    setEditing(row)
    form.setFieldsValue({
      url: row.url,
      description: row.description,
      globallyEnabled: row.globallyEnabled,
      exposedTools: row.exposedTools ?? row.exposedToolNames,
      fetchUrlAllowlist: row.fetchUrlAllowlist?.join('\n') ?? '',
    })
  }

  const columns = [
    { title: '别名', dataIndex: 'alias', key: 'alias', width: 120 },
    { title: '名称', dataIndex: 'displayName', key: 'displayName' },
    {
      title: '全局开关',
      dataIndex: 'globallyEnabled',
      key: 'globallyEnabled',
      render: (v: boolean) => (v ? <Tag color="green">已开放</Tag> : <Tag>未开放</Tag>),
    },
    {
      title: '工具',
      dataIndex: 'exposedToolNames',
      key: 'tools',
      render: (names: string[]) => names.join(', ') || '—',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, row: AdminMcpTemplateItem) => (
        <Space>
          <Button type="link" onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Button
            type="link"
            loading={testMut.isPending && testMut.variables === row.id}
            onClick={() => testMut.mutate(row.id)}
          >
            测试连接
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <PageShell
      title="外部 MCP 模板"
      description="维护 Fetch / Wikipedia / YouTube 三类 MCP 模板（方案 C：P1 仅 Fetch sidecar）"
    >
      <DataCard>
        <Table rowKey="id" loading={isLoading} columns={columns} dataSource={list} pagination={false} />
      </DataCard>

      <Drawer
        title={editing ? `编辑 ${editing.displayName}` : '编辑模板'}
        width={520}
        open={!!editing}
        onClose={() => setEditing(null)}
        extra={
          editing ? (
            <Button
              loading={testMut.isPending && testMut.variables === editing.id}
              onClick={() => testMut.mutate(editing.id)}
            >
              测试连接
            </Button>
          ) : null
        }
        footer={
          <Space>
            <Button onClick={() => setEditing(null)}>取消</Button>
            <Button type="primary" loading={saveMut.isPending} onClick={() => form.submit()}>
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={(values) => saveMut.mutate(values)}>
          <Form.Item name="url" label="MCP URL" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="globallyEnabled" label="对用户开放" valuePropName="checked">
            <Switch />
          </Form.Item>
          {editing?.alias === 'fetch' && (
            <Form.Item name="fetchUrlAllowlist" label="Fetch 域名白名单（每行一个后缀）">
              <Input.TextArea rows={6} />
            </Form.Item>
          )}
          <Form.Item name="exposedTools" label="暴露的工具（最多建议 3 个）">
            <Select mode="multiple" options={toolOptions} placeholder="先测试连接以加载工具列表" />
          </Form.Item>
        </Form>
      </Drawer>
    </PageShell>
  )
}
