import { ExternalLink, MessageSquareText, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { formatDuration } from '../lib/text'

export default function TranscriptsTab({ onAsk }) {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => { setPage(1) }, [q])
  useEffect(() => {
    const id = setTimeout(() => {
      api.episodes(q, page).then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message))
    }, 250)
    return () => clearTimeout(id)
  }, [q, page])

  const pages = data ? Math.max(1, Math.ceil(data.total / 24)) : 1
  return (
    <section className="mx-auto w-full max-w-5xl px-3 py-6 sm:px-6 lg:px-8" aria-label="Transcripts">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-medium tracking-tight">Transcript library</h2>
          <p className="mt-1 text-sm text-muted">Search by guest, title or topic</p>
        </div>
        <label className="relative w-full sm:w-80">
          <span className="sr-only">Search episodes</span>
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search episodes…" className="field !rounded-full !pl-9" />
        </label>
      </div>

      {err && <p role="alert" className="rounded-lg border border-danger/50 bg-danger/10 p-3 text-sm text-danger">{err}</p>}
      {data && data.items.length === 0 && (
        <p className="card p-6 text-center text-muted">{q ? 'No episodes match that search.' : 'No episodes ingested yet. Run the ingestion script (see README).'}</p>
      )}

      <ul className="grid gap-3 md:grid-cols-2">
        {data?.items.map((e) => (
          <li key={e.id} className="card flex flex-col gap-3 p-4">
            <div>
              <p className="label !text-accent">{e.guest || 'Guest'}</p>
              <h3 className="mt-1 line-clamp-2 font-sans text-base font-semibold leading-snug">{e.title}</h3>
              <p className="mt-1 text-xs text-muted">{[e.publish_date, formatDuration(e.duration_seconds)].filter(Boolean).join(' · ')}</p>
            </div>
            <div className="mt-auto flex items-center gap-2">
              <button type="button" className="btn-secondary !py-1 !text-xs"
                onClick={() => onAsk(`Summarize the key lessons from ${e.guest ? `${e.guest}'s` : 'this'} episode "${e.title}"`)}>
                <MessageSquareText size={13} aria-hidden /> Ask about this
              </button>
              {e.youtube_url && (
                <a href={e.youtube_url} target="_blank" rel="noopener noreferrer" className="btn-ghost !py-1 !text-xs">
                  Watch <ExternalLink size={12} aria-hidden />
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>

      {pages > 1 && (
        <nav className="mt-6 flex items-center justify-center gap-3" aria-label="Pagination">
          <button type="button" className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span className="text-sm text-muted">Page {page} of {pages}</span>
          <button type="button" className="btn-secondary" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </nav>
      )}
    </section>
  )
}
