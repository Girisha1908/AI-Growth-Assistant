import { BookmarkPlus, Check, Copy, Download, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { downloadText, slugify } from '../lib/text'
import HtmlSandbox from './HtmlSandbox'
import MarkdownView from './MarkdownView'

export default function ArtifactPanel({ artifact, onClose, onSaved }) {
  const [view, setView] = useState('preview')
  const [copied, setCopied] = useState(false)
  const [saved, setSaved] = useState(false)
  const isHtml = artifact.type === 'html'

  useEffect(() => { setView('preview'); setSaved(false) }, [artifact.id, artifact.content])
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const copy = async () => {
    try { await navigator.clipboard.writeText(artifact.content); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* ignore */ }
  }
  const download = () => downloadText(`${slugify(artifact.title)}.${isHtml ? 'html' : 'md'}`, artifact.content, isHtml ? 'text/html' : 'text/markdown')
  const save = async () => {
    await api.saveNote({ title: artifact.title, kind: artifact.type, content: artifact.content })
    setSaved(true)
    onSaved?.()
  }

  return (
    <aside aria-label={`Artifact: ${artifact.title}`} className="flex h-full min-h-0 flex-col bg-surface">
      <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
        <div className="min-w-0">
          <h2 className="truncate font-sans text-sm font-semibold">{artifact.title}</h2>
          <p className="text-xs text-muted">{isHtml ? 'HTML' : 'Document'}</p>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <div role="tablist" aria-label="View" className="mr-1 flex rounded-full bg-trough p-0.5 text-xs font-semibold">
            {[['preview', 'Preview'], ['code', 'Code']].map(([id, label]) => (
              <button key={id} role="tab" type="button" aria-selected={view === id} onClick={() => setView(id)}
                className={`rounded-full px-3 py-1 ${view === id ? 'bg-raised text-ink' : 'text-muted'}`}>{label}</button>
            ))}
          </div>
          <button type="button" className="btn-ghost !p-1.5" aria-label="Copy" onClick={copy}>{copied ? <Check size={16} /> : <Copy size={16} />}</button>
          <button type="button" className="btn-ghost !p-1.5" aria-label="Download" onClick={download}><Download size={16} /></button>
          <button type="button" className="btn-ghost !p-1.5" aria-label="Save to library" disabled={saved} onClick={save}>{saved ? <Check size={16} /> : <BookmarkPlus size={16} />}</button>
          <button type="button" className="btn-ghost !p-1.5" aria-label="Close" onClick={onClose}><X size={17} /></button>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-8">
        {view === 'code' ? (
          <pre className="whitespace-pre-wrap rounded-lg bg-trough p-4 text-[13px] leading-relaxed" tabIndex={0}>{artifact.content}</pre>
        ) : isHtml ? (
          <div className="h-full min-h-[420px]"><HtmlSandbox html={artifact.content} title={artifact.title} /></div>
        ) : (
          <MarkdownView text={artifact.content} sourceCount={artifact.sourcesCount || 0} className="prose-serif" />
        )}
      </div>
    </aside>
  )
}
