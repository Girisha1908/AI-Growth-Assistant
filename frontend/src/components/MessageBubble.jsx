import { BookmarkPlus, Check, ChevronRight, Copy, FileText, Info } from 'lucide-react'
import { useState } from 'react'
import { api } from '../lib/api'
import MarkdownView from './MarkdownView'
import SourceCards from './SourceCards'

const REFUSAL = "I don't have enough information from the transcripts"

export function UserBubble({ m }) {
  return (
    <div className="flex justify-end">
      <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl bg-raised px-4 py-3 text-[15px] leading-relaxed ${m.failed ? 'ring-1 ring-danger' : ''}`}>
        {m.content}
        {m.failed && <p className="mt-1 text-xs text-danger">Not sent</p>}
      </div>
    </div>
  )
}

function details(meta = {}) {
  return [meta.provider && `${meta.provider}${meta.model ? ` · ${meta.model}` : ''}`,
    meta.latency_ms != null && `${(meta.latency_ms / 1000).toFixed(1)}s`,
    meta.retrieval && `${meta.retrieval.returned} excerpts`,
    meta.word_count && `${meta.word_count} words`].filter(Boolean).join(' · ')
}

export function AssistantBubble({ m, onOpenArtifact, onSaved }) {
  const [copied, setCopied] = useState(false)
  const [saved, setSaved] = useState(false)
  const [activeN, setActiveN] = useState(null)
  const refused = m.content.startsWith(REFUSAL) && !m.sources?.length
  const count = m.sources?.length || 0

  const copy = async () => {
    try { await navigator.clipboard.writeText(m.content); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* ignore */ }
  }
  const save = async () => {
    await api.saveNote({ title: m.content.slice(0, 80).replace(/\s+/g, ' '), kind: 'answer', content: m.content, sources: m.sources || null })
    setSaved(true)
    onSaved?.()
  }
  const cite = (n) => {
    setActiveN(n)
    document.getElementById(`src-${m.id}-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <article className="min-w-0">
      {refused ? (
        <p className="flex items-start gap-2 text-[15px] text-muted" role="note">
          <Info size={17} className="mt-0.5 shrink-0 text-info" aria-hidden />
          <span>That isn’t covered by the transcripts, so I won’t guess. Try rephrasing, or browse the Transcripts section.</span>
        </p>
      ) : (
        <MarkdownView text={m.content} sourceCount={count} onCite={cite} className="prose-serif" />
      )}

      {m.artifact && (
        <button type="button" onClick={() => onOpenArtifact({ id: m.id, ...m.artifact, sourcesCount: count })}
          className="mt-3 flex w-full max-w-md items-center gap-3 rounded-xl border border-line bg-surface p-3 text-left transition hover:border-accent/60">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-on-accent-soft"><FileText size={18} aria-hidden /></span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">{m.artifact.title}</span>
            <span className="text-xs text-muted">{m.artifact.type === 'html' ? 'HTML page' : 'Document'} · Click to open</span>
          </span>
          <ChevronRight size={16} className="text-muted" aria-hidden />
        </button>
      )}

      <SourceCards sources={m.sources} messageId={m.id} activeN={activeN} onSelect={setActiveN} />

      <div className="mt-2 flex items-center gap-0.5 text-muted" title={details(m.meta)}>
        <button type="button" className="btn-ghost !p-1.5" aria-label="Copy" onClick={copy}>{copied ? <Check size={15} /> : <Copy size={15} />}</button>
        <button type="button" className="btn-ghost !p-1.5" aria-label="Save to library" disabled={saved} onClick={save}>{saved ? <Check size={15} /> : <BookmarkPlus size={15} />}</button>
      </div>
    </article>
  )
}
