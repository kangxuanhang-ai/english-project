import { Button, Card, Form, Input, message, Typography } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '@/apis/auth'
import { useUserStore } from '@/stores/user'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setUser = useUserStore((s) => s.setUser)

  const onFinish = async (values: { phone: string; password: string }) => {
    setLoading(true)
    try {
      const res = await login(values.phone, values.password)
      if (res.code !== 200) {
        message.error(res.message || '登录失败')
        return
      }
      if (res.data.role !== 'admin') {
        message.error('无管理员权限')
        return
      }
      setUser(res.data)
      message.success('登录成功')
      navigate('/')
    } catch {
      message.error('登录失败，请检查账号密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-login-root">
      <div className="admin-login-brand">
        <div className="admin-login-brand-inner">
          <div className="admin-login-pill">English Learning Platform</div>
          <h1 className="admin-login-title">运营管理后台</h1>
          <p className="admin-login-subtitle">知识库 · 用户 · 课程 · 数据，一站管理</p>
          <ul className="admin-login-bullets">
            <li>仪表盘运营概览</li>
            <li>知识库 RAG 文档管理</li>
            <li>订单与用户数据监控</li>
          </ul>
        </div>
      </div>
      <div className="admin-login-form-side">
        <Card className="admin-login-form-card" bordered={false}>
          <Typography.Title level={4} style={{ marginBottom: 4 }}>
            管理后台登录
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 24 }}>
            使用管理员账号登录
          </Typography.Paragraph>
          <Form layout="vertical" onFinish={onFinish}>
            <Form.Item
              name="phone"
              label="手机号"
              rules={[
                { required: true, message: '请输入手机号' },
                { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' },
              ]}
            >
              <Input placeholder="13800000000" size="large" />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="admin123" size="large" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>
              登录
            </Button>
          </Form>
          <Typography.Text
            type="secondary"
            style={{ fontSize: 13, display: 'block', marginTop: 16, textAlign: 'center' }}
          >
            非管理员账号将无法进入
          </Typography.Text>
        </Card>
      </div>
    </div>
  )
}
