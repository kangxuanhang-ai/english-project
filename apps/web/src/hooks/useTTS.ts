import { ref } from 'vue'

export function useTTS() {
    const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
    const isSpeaking = ref(false)

    function stripForSpeech(text: string): string {
        return text
            .replace(/<[^>]+>/g, '')
            .replace(/[*#`_~\[\]()]/g, '')
            .replace(/\s+/g, ' ')
            .trim()
    }

    function speak(text: string, lang = 'zh-CN') {
        if (!supported || !text) return
        const plain = stripForSpeech(text)
        if (!plain) return
        window.speechSynthesis.cancel()
        const utterance = new SpeechSynthesisUtterance(plain)
        utterance.lang = lang
        utterance.onend = () => {
            isSpeaking.value = false
        }
        utterance.onerror = () => {
            isSpeaking.value = false
        }
        isSpeaking.value = true
        window.speechSynthesis.speak(utterance)
    }

    function stop() {
        window.speechSynthesis.cancel()
        isSpeaking.value = false
    }

    return { supported, isSpeaking, speak, stop, stripForSpeech }
}
