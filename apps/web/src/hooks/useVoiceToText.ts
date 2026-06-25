import { ref } from 'vue'

export interface Options {
    lang?: string
    continuous?: boolean
    interimResults?: boolean
    maxAlternatives?: number
}

let instance: SpeechRecognition | null = null
let storedOptions: Options = {}

function createRecognition(options: Options): SpeechRecognition {
    const speechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!speechRecognition) {
        throw new Error('SpeechRecognition is not supported in this browser')
    }
    const {
        lang = 'zh-CN',
        continuous = false,
        interimResults = false,
        maxAlternatives = 1,
    } = options
    const rec = new speechRecognition()
    rec.lang = lang
    rec.continuous = continuous
    rec.interimResults = interimResults
    rec.maxAlternatives = maxAlternatives
    return rec
}

function rebuildInstance(options: Options): SpeechRecognition {
    try {
        instance?.stop()
    } catch {
        // 可能未在录音
    }
    instance = createRecognition(options)
    storedOptions = { ...options }
    return instance
}

export const useVoiceToText = (options: Options) => {
    let recognition = instance ?? rebuildInstance(options)
    if (options.lang && options.lang !== storedOptions.lang) {
        recognition = rebuildInstance({ ...storedOptions, ...options })
    }

    const isRecording = ref(false)

    const bindOnEnd = () => {
        recognition.onend = () => {
            isRecording.value = false
        }
    }
    bindOnEnd()

    const setLang = (newLang: string) => {
        if (storedOptions.lang === newLang) return
        if (isRecording.value) {
            try {
                recognition.stop()
            } catch {
                // ignore
            }
            isRecording.value = false
        }
        recognition = rebuildInstance({ ...storedOptions, lang: newLang })
        bindOnEnd()
    }

    const start = (callback?: (result: string) => void) => {
        isRecording.value = true
        recognition.onresult = (event) => {
            let fullText = ''
            for (let i = 0; i < event.results.length; i++) {
                fullText += event.results[i][0].transcript
            }
            callback?.(fullText)
        }
        recognition.start()
    }

    const stop = () => {
        isRecording.value = false
        recognition.stop()
    }

    return {
        isRecording,
        start,
        stop,
        setLang,
    }
}
