import type { ChatPurchaseBlock } from '@en/common/chat'

const MARKER_START = '__PURCHASE_JSON__'
const MARKER_END = '__END_PURCHASE_JSON__'

const VALID_ACTIONS = new Set(['confirm', 'resume_pay', 'already_owned', 'not_found'])

function parsePurchaseJson(jsonText: string): ChatPurchaseBlock | null {
    try {
        const parsed = JSON.parse(jsonText)
        if (!VALID_ACTIONS.has(parsed.action)) return null
        return {
            action: parsed.action,
            message: parsed.message,
            selectedIndex: parsed.selected_index ?? parsed.selectedIndex,
            recommendTitles: parsed.recommend_titles ?? parsed.recommendTitles,
            course: parsed.course,
        }
    } catch {
        return null
    }
}

/** 解析 course_purchase 工具输出（与后端 _extract_purchase_block 规则对齐） */
export function parsePurchaseBlock(raw: string): ChatPurchaseBlock | null {
    if (!raw) return null

    if (raw.includes(MARKER_START) && raw.includes(MARKER_END)) {
        const jsonPart = raw.split(MARKER_START)[1]?.split(MARKER_END)[0]?.trim()
        if (jsonPart) {
            const block = parsePurchaseJson(jsonPart)
            if (block) return block
        }
    }

    return parsePurchaseJson(raw.trim())
}
