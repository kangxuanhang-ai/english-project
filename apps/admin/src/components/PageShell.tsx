import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Space, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

type PageShellProps = {
  title: string
  description?: string
  extra?: ReactNode
  back?: boolean
  children: ReactNode
}

export default function PageShell({ title, description, extra, back, children }: PageShellProps) {
  const navigate = useNavigate()

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 20,
          gap: 16,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          {back && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(-1)}
              style={{ marginBottom: 8, paddingInline: 0 }}
            >
              返回
            </Button>
          )}
          <Typography.Title
            level={4}
            style={{ margin: 0, fontWeight: 600, letterSpacing: '-0.02em' }}
          >
            {title}
          </Typography.Title>
          {description && (
            <Typography.Text type="secondary" style={{ fontSize: 13, marginTop: 4, display: 'block' }}>
              {description}
            </Typography.Text>
          )}
        </div>
        {extra && <Space wrap>{extra}</Space>}
      </div>
      {children}
    </div>
  )
}
