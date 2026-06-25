import { Card, Statistic } from 'antd'
import type { ReactNode } from 'react'

type StatCardProps = {
  title: string
  value: number | string
  prefix?: ReactNode
  suffix?: ReactNode
  icon: ReactNode
  loading?: boolean
  onClick?: () => void
}

export default function StatCard({
  title,
  value,
  prefix,
  suffix,
  icon,
  loading,
  onClick,
}: StatCardProps) {
  return (
    <Card
      bordered={false}
      loading={loading}
      className="admin-stat-card"
      styles={{ body: { padding: 20 } }}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : undefined }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        <div className="admin-stat-card-icon">{icon}</div>
      </div>
      <Statistic
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ fontSize: 28, fontWeight: 700, color: '#18181b' }}
      />
      <div style={{ marginTop: 8, fontSize: 14, color: '#71717a' }}>{title}</div>
    </Card>
  )
}
