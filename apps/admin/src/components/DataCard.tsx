import { Card } from 'antd'
import type { ReactNode } from 'react'

type DataCardProps = {
  title?: ReactNode
  children: ReactNode
  flush?: boolean
  loading?: boolean
}

export default function DataCard({ title, children, flush, loading }: DataCardProps) {
  return (
    <Card
      title={title}
      bordered={false}
      loading={loading}
      style={{ boxShadow: 'var(--admin-shadow-card)' }}
      styles={{ body: { padding: flush ? 0 : 20 } }}
    >
      {children}
    </Card>
  )
}
