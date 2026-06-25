import { Button, Card, Form, Input, InputNumber, Select, Space, Upload, message } from 'antd'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCourse, fetchCourse, updateCourse, uploadCourseCover } from '@/apis/admin'
import { PageShell } from '@/components'
import { COURSE_VALUE_OPTIONS } from '@en/common/admin'

export default function CourseFormPage() {
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id && id !== 'new')
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [coverUrl, setCoverUrl] = useState<string>()
  const urlValue = Form.useWatch('url', form)

  const { data: courseData } = useQuery({
    queryKey: ['admin-course', id],
    queryFn: () => fetchCourse(id!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (courseData?.data) {
      form.setFieldsValue(courseData.data)
      setCoverUrl(courseData.data.url)
    }
  }, [courseData, form])

  const saveMut = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (isEdit) {
        return updateCourse(id!, values)
      }
      return createCourse(values as never)
    },
    onSuccess: () => {
      message.success(isEdit ? '更新成功' : '创建成功')
      navigate('/courses')
    },
    onError: () => message.error('保存失败'),
  })

  const preview = urlValue || coverUrl

  return (
    <PageShell title={isEdit ? '编辑课程' : '新建课程'} back>
      <Card bordered={false} style={{ maxWidth: 640, boxShadow: 'var(--admin-shadow-card)' }}>
        <Form form={form} layout="vertical" onFinish={(v) => saveMut.mutate(v)}>
          <Form.Item name="name" label="课程名称" rules={[{ required: true, message: '请输入课程名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="value" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select options={COURSE_VALUE_OPTIONS} />
          </Form.Item>
          <Form.Item name="teacher" label="讲师" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="url"
            label="封面"
            rules={[{ required: true, message: '请上传封面或填写 URL' }]}
            extra="上传后 C 端课程列表将直接使用该图片地址"
          >
            <Input placeholder="上传封面或粘贴图片 URL" />
          </Form.Item>
          <Upload
            listType="picture-card"
            showUploadList={false}
            beforeUpload={(file) => {
              void uploadCourseCover(file as File)
                .then((res) => {
                  form.setFieldValue('url', res.data.url)
                  setCoverUrl(res.data.url)
                  message.success('封面上传成功')
                })
                .catch(() => message.error('上传失败'))
              return false
            }}
          >
            {preview ? (
              <img src={preview} alt="cover" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              '+ 上传封面'
            )}
          </Upload>
          <Form.Item name="price" label="价格" rules={[{ required: true }]}>
            <InputNumber min={0} precision={2} style={{ width: '100%' }} prefix="¥" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Space>
            <Button onClick={() => navigate('/courses')}>取消</Button>
            <Button type="primary" htmlType="submit" loading={saveMut.isPending}>
              保存
            </Button>
          </Space>
        </Form>
      </Card>
    </PageShell>
  )
}
