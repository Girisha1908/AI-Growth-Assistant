import { AlertTriangle, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { AssistantBubble, UserBubble } from './MessageBubble'

function Thinking({ mode }) {
  const [s, setS] = useState(0)
  useEffect(() => { const id = setInterval(() => setS((x) => x + 1), 1000); return () => clearInterval(id) }, [])
  return (
    <div className="flex items-center gap-3 text-sm text-muted" role="status" aria-live="polite">
      <span className="flex gap-1" aria-hidden>
        {[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 animate-pulse rounded-full bg-accent" style={{ animationDelay: `${i * 150}ms` }} />)}
      </span>
      <span>
        {mode === 'ship30' ? 'Writing your essay section by section' : 'Thinking'}
        {s >= 10 && ` · ${s}s`}
        {s >= 20 && ' · local models can take a minute. You can stop and try a shorter request.'}
      </span>
    </div>
  )
}

function ErrorCard({ error, onRetry }) {
  return (
    <div role="alert" className="flex gap-3 rounded-xl border border-danger/40 bg-danger/10 p-4">
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-danger" aria-hidden />
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-semibold text-danger">{error.message}</p>
        {error.hint && <p className="mt-1 text-muted">{error.hint}</p>}
        <button type="button" className="btn-secondary mt-3 !py-1" onClick={onRetry}><RotateCcw size={14} aria-hidden /> Retry</button>
      </div>
    </div>
  )
}

export default function MessageList({ messages, sending, sendingMode, error, onRetry, onOpenArtifact, onSaved }) {
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages.length, sending, error])
  return (
    <div className="flex flex-col gap-8" aria-live="polite" aria-label="Conversation">
      {messages.map((m) => (m.role === 'user'
        ? <UserBubble key={m.id} m={m} />
        : <AssistantBubble key={m.id} m={m} onOpenArtifact={onOpenArtifact} onSaved={onSaved} />))}
      {sending && <Thinking mode={sendingMode} />}
      {error && !sending && <ErrorCard error={error} onRetry={onRetry} />}
      <div ref={endRef} />
    </div>
  )
}
