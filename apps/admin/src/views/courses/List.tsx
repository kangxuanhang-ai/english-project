import { Button, Space, Table, Tag, message } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchCourses, publishCourse, unpublishCourse } from '@/apis/admin'
import { DataCard, PageShell } from '@/components'
import type { AdminCourse } from '@en/common/admin'

export default function CourseListPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-courses', page, pageSize],
    queryFn: () => fetchCourses({ page, pageSize }),
  })

  const publishMut = useMutation({
    mutationFn: (id: string) => publishCourse(id),
    onSuccess: () => {
      message.success('已上架')
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] })
    },
  })

  const unpublishMut = useMutation({
    mutationFn: (id: string) => unpublishCourse(id),
    onSuccess: () => {
      message.success('已下架')
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] })
    },
  })

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'value', key: 'value' },
    { title: '讲师', dataIndex: 'teacher', key: 'teacher' },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      align: 'right' as const,
      render: (v: number) => <span style={{ fontWeight: 600 }}>¥{v.toFixed(2)}</span>,
    },
    {
      title: '状态',
      dataIndex: 'isPublished',
      key: 'isPublished',
      render: (v: boolean) => (v ? <Tag color="success">上架</Tag> : <Tag color="default">下架</Tag>),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: AdminCourse) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/courses/${record.id}/edit`)}>
            编辑
          </Button>
          {record.isPublished ? (
            <Button type="link" danger onClick={() => unpublishMut.mutate(record.id)}>
              下架
            </Button>
          ) : (
            <Button type="link" onClick={() => publishMut.mutate(record.id)}>
              上架
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <PageShell
      title="课程管理"
      description="管理平台课程与上下架状态"
      extra={
        <Button type="primary" onClick={() => navigate('/courses/new')}>
          新建课程
        </Button>
      }
    >
      <DataCard flush>
        <Table<AdminCourse>
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
