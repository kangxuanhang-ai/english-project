import type { ChatGrammarBlock } from '@en/common/chat'

const FIELD_PATTERNS: { key: keyof ChatGrammarBlock; labels: string[] }[] = [
    { key: 'error', labels: ['语法错误'] },
    { key: 'original', labels: ['原句'] },
    { key: 'corrected', labels: ['修正'] },
    { key: 'explanation', labels: ['说明', '解释'] },
]

function pickField(text: string, labels: string[]): string {
    for (const label of labels) {
        const re = new RegExp(`${label}[：:]\\s*(.+?)(?=\\n|$)`, 's')
        const m = text.match(re)
        if (m?.[1]) return m[1].trim()
    }
    return ''
}

/** 解析 grammar_check 工具输出（与后端 _extract_grammar_block 规则对齐） */
export function parseGrammarBlock(raw: string): ChatGrammarBlock | null {
    const text = (raw ?? '').trim()
    if (!text) return null

    if (/语法正确/.test(text) && !/语法错误[：:]/.test(text)) {
        return { ok: true, summary: '语法正确，没有发现错误。' }
    }

    const block: ChatGrammarBlock = { ok: false }
    for (const { key, labels } of FIELD_PATTERNS) {
        const val = pickField(text, labels)
        if (val) block[key] = val
    }

    if (!block.error && !block.original && !block.corrected) return null
    return block
}
