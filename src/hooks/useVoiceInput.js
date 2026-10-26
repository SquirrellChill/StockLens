import { useCallback, useEffect, useRef, useState } from 'react'

/** Thin wrapper around the browser Web Speech API. */
export function useVoiceInput({ lang = 'en-US', onResult } = {}) {
  const Recognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
  const supported = !!Recognition
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const ref = useRef(null)
  const onResultRef = useRef(onResult)
  onResultRef.current = onResult

  useEffect(() => () => ref.current?.abort?.(), [])

  const start = useCallback(() => {
    if (!Recognition) {
      setError('Voice recognition is not supported in this browser. Add sales manually instead.')
      return
    }
    setError('')
    setTranscript('')
    const r = new Recognition()
    r.lang = lang
    r.onstart = () => setListening(true)
    r.onend = () => setListening(false)
    r.onerror = (e) => setError(e.error === 'not-allowed' ? 'Please allow microphone access to record sales.' : 'We could not hear that. Please try again.')
    r.onresult = (e) => {
      const text = e.results[0][0].transcript
      setTranscript(text)
      onResultRef.current?.(text)
    }
    ref.current = r
    r.start()
  }, [Recognition, lang])

  const stop = useCallback(() => ref.current?.stop?.(), [])

  return { supported, listening, transcript, error, start, stop, setTranscript }
}
