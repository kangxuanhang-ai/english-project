import { marked } from 'marked'
import hljs from 'highlight.js'
import { markedHighlight } from 'marked-highlight'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/github-dark.css'

marked.use(markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value
        }
        return hljs.highlightAuto(code).value
    },
}))

export function parseMarkdown(content: string): string {
    return content ? DOMPurify.sanitize(marked.parse(content) as string) : ''
}
