/** 模型偶发复述的 JSON 说明话术 */
const JSON_INSTRUCTION_LEAK = /请遵循|如下.*JSON|开始处理输入|推荐输出|输入数据后/i

/** 移除 markdown 代码块中的推荐 JSON 泄漏 */
function stripRecommendCodeFences(text: string): string {
    return text.replace(/```[\w]*\n?[\s\S]*?```/g, (block) => {
        if (looksLikeRecommendJsonFragment(block) || /"courses"/.test(block)) return ''
        return block
    })
}

/** 是否整行属于应丢弃的泄漏内容 */
function isLeakedRecommendLine(line: string): boolean {
    const t = line.trim()
    if (!t) return false
    if (JSON_INSTRUCTION_LEAK.test(t)) return true
    if (/^\s*"[a-z_]+"\s*:?\s*[,{[]]?$/.test(t)) return true
    if (t === '"courses"' || t === '"courses":' || t === '{') return true
    if (/^[\[{",}\]]+$/.test(t)) return true
    if (/^\s*```/.test(t)) return true
    return looksLikeRecommendJsonFragment(t) && !/[\u4e00-\u9fff]{4,}/.test(t)
}
function isRecommendationJson(text: string): boolean {
    try {
        const parsed = JSON.parse(text)
        return Array.isArray(parsed.courses)
    } catch {
        return false
    }
}

/** 是否为推荐 JSON 片段（含流式中间 chunk，可能没有 `{`） */
export function looksLikeRecommendJsonFragment(text: string): boolean {
    return /"courses"\s*:/.test(text)
        || /"course_id"\s*:/.test(text)
        || /"match_score"\s*:/.test(text)
        || /"daily_plan"\s*:/.test(text)
        || /"new_words_per_day"\s*:/.test(text)
        || /"review_frequency"\s*:/.test(text)
        || /"estimated_completion"\s*:/.test(text)
}

/** 从 start 位置的 `{` 起匹配完整 JSON 对象 */
function findBalancedJsonEnd(text: string, start: number): number {
    if (text[start] !== '{') return -1

    let depth = 0
    let inString = false
    let escape = false

    for (let i = start; i < text.length; i++) {
        const char = text[i]
        if (inString) {
            if (escape) escape = false
            else if (char === '\\') escape = true
            else if (char === '"') inString = false
            continue
        }
        if (char === '"') {
            inString = true
            continue
        }
        if (char === '{') depth++
        else if (char === '}') {
            depth--
            if (depth === 0) return i
        }
    }
    return -1
}

/** 是否主要为 JSON 泄漏（无 `{` 的中间 chunk 或整段复述） */
function isMostlyRecommendJsonLeak(text: string): boolean {
    const trimmed = text.trim()
    if (!trimmed || !looksLikeRecommendJsonFragment(trimmed)) return false
    if (/^[\[{,"]/.test(trimmed)) return true
    const chinese = (trimmed.match(/[\u4e00-\u9fff]/g) || []).length
    return chinese / trimmed.length < 0.28
}

/** 去掉 JSON 键名残留，如 "courses我强烈推荐 → 我强烈推荐 */
function polishProse(text: string): string {
    if (!text) return text
    const chineseIdx = text.search(/[\u4e00-\u9fff]/)
    if (chineseIdx > 0) {
        const prefix = text.slice(0, chineseIdx)
        if (
            /courses|course_id|match_score|daily_plan|summary/.test(prefix)
            || !prefix.replace(/[\s"'{[\]},:]+/g, '')
        ) {
            text = text.slice(chineseIdx)
        }
    }
    return text.replace(/^[\s"'{[\]},:]+/, '')
}

/** 从混合文本中提取 JSON 后面的自然语言 */
function extractNaturalLanguageTail(text: string): string {
    const lastBrace = text.lastIndexOf('}')
    if (lastBrace !== -1 && lastBrace < text.length - 1) {
        const tail = text.slice(lastBrace + 1).trim()
        if (tail && /[\u4e00-\u9fff]/.test(tail) && !looksLikeRecommendJsonFragment(tail)) {
            return polishProse(tail)
        }
    }

    const lines = text.split('\n')
    const proseLines = lines.filter((line) => {
        const t = line.trim()
        if (!t) return false
        if (/^\s*"[a-z_]+"\s*:/.test(t)) return false
        if (/^[\[{],/.test(t)) return false
        return /[\u4e00-\u9fff]/.test(t) && !looksLikeRecommendJsonFragment(t)
    })
    if (proseLines.length) return polishProse(proseLines.join('\n').trim())

    const match = text.match(/([\u4e00-\u9fff][\u4e00-\u9fff，。！？、；：""''（）\s\d%《》]+)/)
    if (match?.[1] && !looksLikeRecommendJsonFragment(match[1])) {
        return polishProse(match[1].trim())
    }
    return ''
}

/** 移除文本中泄漏的课程推荐 JSON（含多 chunk 流式、无 `{` 片段） */
export function stripRecommendationJson(text: string): string {
    if (!text) return text

    text = text.replace(/__RECOMMEND_JSON__[\s\S]*?__END_RECOMMEND_JSON__/g, '')

    if (!text.includes('{') && !text.includes('[')) {
        if (isMostlyRecommendJsonLeak(text)) return extractNaturalLanguageTail(text)
        if (!looksLikeRecommendJsonFragment(text)) return polishProse(text)
        return extractNaturalLanguageTail(text)
    }

    let result = ''
    let i = 0

    while (i < text.length) {
        const braceStart = text.indexOf('{', i)
        if (braceStart === -1) {
            const remainder = text.slice(i)
            if (isMostlyRecommendJsonLeak(remainder) || looksLikeRecommendJsonFragment(remainder)) {
                const tail = extractNaturalLanguageTail(remainder)
                if (tail) result += tail
            } else {
                result += remainder
            }
            break
        }

        result += text.slice(i, braceStart)
        const braceEnd = findBalancedJsonEnd(text, braceStart)

        if (braceEnd === -1) {
            const tail = text.slice(braceStart)
            if (!looksLikeRecommendJsonFragment(tail)) result += tail
            break
        }

        const candidate = text.slice(braceStart, braceEnd + 1)
        if (isRecommendationJson(candidate) || looksLikeRecommendJsonFragment(candidate)) {
            i = braceEnd + 1
        } else {
            result += candidate
            i = braceEnd + 1
        }
    }

    result = polishProse(result.replace(/\n{3,}/g, '\n\n').trimEnd())
    if (looksLikeRecommendJsonFragment(result) && isMostlyRecommendJsonLeak(result)) {
        return extractNaturalLanguageTail(result)
    }
    return result
}

/** 已有推荐卡片时，更激进地清理 contentAfter */
export function sanitizeContentAfter(text: string, hasRecommendBlock: boolean): string {
    if (!text) return text
    let cleaned = stripRecommendCodeFences(stripRecommendationJson(text))
    if (!hasRecommendBlock) return polishProse(cleaned)

    if (looksLikeRecommendJsonFragment(cleaned) || isMostlyRecommendJsonLeak(cleaned)) {
        cleaned = extractNaturalLanguageTail(cleaned)
    }

    cleaned = cleaned
        .split('\n')
        .filter((line) => !isLeakedRecommendLine(line))
        .join('\n')
        .trim()

    cleaned = polishProse(cleaned)

    // 若清理后只剩极短碎片，丢弃
    if (cleaned.length < 8 && looksLikeRecommendJsonFragment(cleaned)) return ''

    return cleaned
}
