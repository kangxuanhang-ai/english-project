import DOMPurify from 'dompurify'

/** 词库释义：将字面量 \\n 转为换行并安全渲染 */
export function formatWordField(text: string | null | undefined): string {
    if (!text) return ''
    const normalized = text.replace(/\\n/g, '\n')
    if (/<[a-z][\s\S]*>/i.test(normalized)) {
        return DOMPurify.sanitize(normalized)
    }
    const escaped = normalized
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
    return DOMPurify.sanitize(escaped.replace(/\n/g, '<br>'))
}
