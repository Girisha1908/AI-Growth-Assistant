import { ExternalLink } from 'lucide-react'

/** Compact citations: a row of pills; the selected one expands to show the excerpt and a link. */
export default function SourceCards({ sources, messageId, activeN, onSelect }) {
  if (!sources?.length) return null
  const active = sources.find((s) => s.n === activeN)
  return (
    <section aria-label="Sources" className="mt-4">
      <ul className="flex flex-wrap gap-1.5">
        {sources.map((s) => (
          <li key={s.n}>
            <button type="button" id={`src-${messageId}-${s.n}`} aria-pressed={activeN === s.n}
              onClick={() => onSelect(activeN === s.n ? null : s.n)}
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition ${activeN === s.n ? 'border-accent bg-accent-soft text-on-accent-soft' : 'border-line text-muted hover:border-accent/60 hover:text-ink'}`}>
              <span className="font-bold">{s.n}</span>
              <span className="max-w-[11rem] truncate">{s.guest || s.title}</span>
              {s.timestamp && <span className="opacity-70">{s.timestamp}</span>}
            </button>
          </li>
        ))}
      </ul>
      {active && (
        <div className="mt-2 rounded-xl border border-line bg-surface p-3 text-sm">
          <p className="font-semibold">{active.title}</p>
          <p className="mt-1.5 text-muted">“{active.snippet}…”</p>
          {active.url && (
            <a href={active.url} target="_blank" rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline">
              Open on YouTube{active.timestamp ? ` at ${active.timestamp}` : ''} <ExternalLink size={12} aria-hidden />
            </a>
          )}
        </div>
      )}
    </section>
  )
}
