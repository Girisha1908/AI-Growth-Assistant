import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

const KEY = 'lga-session'
const store = {
  get: () => { try { return localStorage.getItem(KEY) } catch { return null } },
  set: (v) => { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY) } catch { /* ignore */ } },
}

/** Conversation state. The server is the source of truth; we only add an optimistic user bubble. */
export function useChat({ onArtifact } = {}) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)
  const lastRequest = useRef(null)

  const loadSession = useCallback(async (id) => {
    try {
      const rows = await api.messages(id)
      setSessionId(id)
      setMessages(rows)
      setError(null)
      store.set(id)
    } catch (e) {
      if (e.status === 404) store.set(null)
    }
  }, [])

  useEffect(() => {
    const saved = store.get()
    if (saved) loadSession(saved)
  }, [loadSession])

  const newChat = useCallback(() => {
    abortRef.current?.abort()
    setSessionId(null)
    setMessages([])
    setError(null)
    setSending(false)
    store.set(null)
  }, [])

  const send = useCallback(async ({ text, mode, provider, personalize }) => {
    const clean = text.trim()
    if (!clean || sending) return
    lastRequest.current = { text: clean, mode, provider, personalize }
    setError(null)
    setSending(true)
    const tempId = `tmp-${Date.now()}`
    setMessages((m) => [...m, { id: tempId, role: 'user', content: clean, mode, created_at: new Date().toISOString() }])
    const controller = new AbortController()
    abortRef.current = controller
    try {
      let id = sessionId
      if (!id) {
        const s = await api.createSession({ client: 'web', locale: navigator.language })
        id = s.session_id
        setSessionId(id)
        store.set(id)
      }
      const res = await api.chat({
        session_id: id, message: clean, mode: mode || 'auto',
        provider: provider || null, personalize: personalize !== false,
      }, controller.signal)
      setMessages((m) => [...m, {
        id: res.message_id, role: 'assistant', content: res.answer, mode: res.mode,
        sources: res.sources, artifact: res.artifact, meta: res.meta, created_at: new Date().toISOString(),
      }])
      if (res.artifact) onArtifact?.({ id: res.message_id, ...res.artifact, sourcesCount: res.sources.length })
    } catch (e) {
      if (e.name === 'AbortError') {
        setMessages((m) => m.filter((x) => x.id !== tempId))
      } else {
        setMessages((m) => m.map((x) => (x.id === tempId ? { ...x, failed: true } : x)))
        setError({ code: e.code, message: e.message, hint: e.hint })
      }
    } finally {
      setSending(false)
      abortRef.current = null
    }
  }, [sessionId, sending, onArtifact])

  const retry = useCallback(() => {
    const req = lastRequest.current
    if (!req) return
    setMessages((m) => m.filter((x) => !x.failed))
    setError(null)
    send(req)
  }, [send])

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return { sessionId, messages, sending, error, send, retry, stop, newChat, loadSession }
}
