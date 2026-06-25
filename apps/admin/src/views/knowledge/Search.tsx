import { Button, Input, InputNumber, Space, Tag, Tooltip, Typography } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { searchKnowledge } from '@/apis/admin'
import { DataCard, EmptyHint, FilterCard, PageShell } from '@/components'
import type { KnowledgeSearchHit } from '@en/common/knowledge'

const SEARCH_EXAMPLES = ['康烜航是谁', '平台打卡规则是什么', '如何购买课程']

export default function KnowledgeSearchPage() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<KnowledgeSearchHit[]>([])
  const [totalTokens, setTotalTokens] = useState(0)

  const runSearch = async (text?: string) => {
    const q = (text ?? query).trim()
    if (!q) return
    if (text) setQuery(text)
    setLoading(true)
    try {
      const res = await searchKnowledge({ q, topK })
      setResults(res.data.results)
      setTotalTokens(res.data.totalTokens)
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageShell title="检索测试" description="测试知识库向量检索效果" back>
      <FilterCard>
        <Space wrap align="center">
          <Tooltip title="最多返回相似度最高的 N 条文档片段，建议 3–10">
            <QuestionCircleOutlined style={{ color: '#71717a' }} />
          </Tooltip>
          <InputNumber
            addonBefore="返回条数"
            min={1}
            max={20}
            value={topK}
            onChange={(v) => setTopK(v ?? 5)}
          />
          <Input
            style={{ width: 360 }}
            placeholder="输入检索问题"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onPressEnter={() => void runSearch()}
          />
          <Button type="primary" loading={loading} onClick={() => void runSearch()}>
            检索
          </Button>
        </Space>
        <Space wrap style={{ marginTop: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            示例：
          </Typography.Text>
          {SEARCH_EXAMPLES.map((text) => (
            <Tag
              key={text}
              style={{ cursor: 'pointer' }}
              onClick={() => void runSearch(text)}
            >
              {text}
            </Tag>
          ))}
        </Space>
      </FilterCard>

      <DataCard>
        {results.length === 0 && !loading ? (
          <EmptyHint description="输入问题后点击检索，或选择上方示例" />
        ) : (
          <>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              共 {results.length} 条，约 {totalTokens} tokens
            </Typography.Text>
            {results.map((hit, i) => (
              <div key={`${hit.documentId}-${hit.chunkIndex}-${i}`} className="admin-search-hit">
                <Space style={{ marginBottom: 8 }}>
                  <Typography.Text strong>{hit.title}</Typography.Text>
                  <Tag color="blue">相似度 {(hit.score * 100).toFixed(1)}%</Tag>
                  <Tag>chunk #{hit.chunkIndex}</Tag>
                </Space>
                <Typography.Paragraph ellipsis={{ rows: 3, expandable: true }} style={{ margin: 0 }}>
                  {hit.content}
                </Typography.Paragraph>
              </div>
            ))}
          </>
        )}
      </DataCard>
    </PageShell>
  )
}
