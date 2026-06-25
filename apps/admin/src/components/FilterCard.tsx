import { Card } from 'antd'
import type { ReactNode } from 'react'

export default function FilterCard({ children }: { children: ReactNode }) {
  return (
    <Card
      bordered={false}
      style={{ marginBottom: 16, boxShadow: 'var(--admin-shadow-card)' }}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {children}
    </Card>
  )
}
