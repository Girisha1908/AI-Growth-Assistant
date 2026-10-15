import { ArrowUp, Check, ChevronDown, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { MODES } from '../lib/text'

function ModeMenu({ mode, setMode }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const current = MODES.find((m) => m.id === mode) || MODES[0]
  useEffect(() => {
    if (!open) return undefined
    const onDoc = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onKey) }
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium text-muted transition hover:bg-raised hover:text-ink">
        {current.short} <ChevronDown size={14} aria-hidden />
      </button>
      {open && (
        <div role="menu" className="card absolute bottom-11 left-0 z-30 w-72 p-1.5">
          {MODES.map((m) => (
            <button key={m.id} type="button" role="menuitemradio" aria-checked={mode === m.id}
              onClick={() => { setMode(m.id); setOpen(false) }}
              className="flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left hover:bg-raised">
              <span className="mt-0.5 w-4 text-accent">{mode === m.id && <Check size={14} />}</span>
              <span><span className="block text-sm font-semibold">{m.label}</span>
                <span className="block text-xs text-muted">{m.blurb}</span></span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Composer({ sending, onSend, onStop, config, mode, setMode, text, setText, provider, setProvider, autoFocus }) {
  const taRef = useRef(null)
  const current = MODES.find((m) => m.id === mode) || MODES[0]
  const providers = config?.providers || []
  const effective = provider || config?.provider || 'ollama'

  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [text])
  useEffect(() => { if (autoFocus) taRef.current?.focus() }, [autoFocus, mode])

  const submit = () => { if (text.trim() && !sending) onSend() }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit() }} aria-label="Message composer"
      className="rounded-2xl border border-line bg-surface p-3 shadow-card transition focus-within:border-accent/60">
      <label htmlFor="composer-input" className="sr-only">Your message</label>
      <textarea id="composer-input" ref={taRef} rows={1} value={text} maxLength={4000}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        placeholder={current.placeholder}
        className="block max-h-56 w-full resize-none bg-transparent px-2 py-1.5 text-[16px] text-ink outline-none placeholder:text-muted/70 focus-visible:ring-0 focus-visible:ring-offset-0" />
      <div className="mt-1 flex items-center justify-between">
        <ModeMenu mode={mode} setMode={setMode} />
        <div className="flex items-center gap-2">
          <select value={effective} onChange={(e) => setProvider(e.target.value)} aria-label="Model"
            className="max-w-[10rem] truncate rounded-full bg-transparent px-2 py-1 text-xs font-medium text-muted hover:text-ink">
            {providers.map((p) => (
              <option key={p.name} value={p.name} disabled={!p.configured} className="bg-surface text-ink">
                {p.label}{p.configured ? '' : ' (no key)'}
              </option>
            ))}
          </select>
          {sending ? (
            <button type="button" onClick={onStop} aria-label="Stop"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-on-accent"><Square size={14} fill="currentColor" /></button>
          ) : (
            <button type="submit" disabled={!text.trim()} aria-label="Send message"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-on-accent transition hover:opacity-90"><ArrowUp size={18} /></button>
          )}
        </div>
      </div>
    </form>
  )
}
