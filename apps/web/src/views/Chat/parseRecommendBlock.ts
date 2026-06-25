import type { ChatRecommendBlock } from '@en/common/chat'

const MARKER_START = '__RECOMMEND_JSON__'
const MARKER_END = '__END_RECOMMEND_JSON__'

function parseRecommendJson(jsonText: string): ChatRecommendBlock | null {
    try {
        const parsed = JSON.parse(jsonText)
        if (!Array.isArray(parsed.courses) || !parsed.courses.length) return null
        return {
            courses: parsed.courses,
            daily_plan: parsed.daily_plan,
            summary: parsed.summary,
        }
    } catch {
        return null
    }
}

/** 解析 course_recommendation 工具输出（与后端 _extract_recommend_block 规则对齐） */
export function parseRecommendBlock(raw: string): ChatRecommendBlock | null {
    if (!raw) return null

    if (raw.includes(MARKER_START) && raw.includes(MARKER_END)) {
        const jsonPart = raw.split(MARKER_START)[1]?.split(MARKER_END)[0]?.trim()
        if (jsonPart) {
            const block = parseRecommendJson(jsonPart)
            if (block) return block
        }
    }

    return parseRecommendJson(raw.trim())
}
