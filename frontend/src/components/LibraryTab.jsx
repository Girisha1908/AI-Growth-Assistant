import { Download, FileText, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { downloadText, relativeTime, slugify } from '../lib/text'

const KIND_LABEL = { markdown: 'Markdown', html: 'HTML', answer: 'Answer', note: 'Note' }

export default function LibraryTab({ onOpen, refreshKey }) {
  const [notes, setNotes] = useState(null)
  const [err, setErr] = useState(null)
  const load = useCallback(() => api.notes().then((n) => { setNotes(n); setErr(null) }).catch((e) => setErr(e.message)), [])
  useEffect(() => { load() }, [load, refreshKey])

  const remove = async (id) => { await api.deleteNote(id).catch(() => {}); load() }
  const download = (n) => downloadText(`${slugify(n.title)}.${n.kind === 'html' ? 'html' : 'md'}`, n.content, n.kind === 'html' ? 'text/html' : 'text/markdown')

  return (
    <section className="mx-auto w-full max-w-5xl px-3 py-6 sm:px-6 lg:px-8" aria-label="Saved artifacts">
      <h2 className="text-3xl font-medium tracking-tight">Your library</h2>
      <p className="mb-6 mt-1 text-sm text-muted">Everything you saved.</p>
      {err && <p role="alert" className="rounded-lg border border-danger/50 bg-danger/10 p-3 text-sm text-danger">{err}</p>}
      {notes?.length === 0 && <p className="card p-8 text-center text-muted">Nothing saved yet. Use “Save to library” on any answer or artifact.</p>}
      <ul className="grid gap-3 md:grid-cols-2">
        {notes?.map((n) => (
          <li key={n.id} className="card flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between">
              <span className="chip">{KIND_LABEL[n.kind] || n.kind}</span>
              <span className="text-xs text-muted">{relativeTime(n.created_at)}</span>
            </div>
            <h3 className="line-clamp-2 font-sans text-base font-semibold">{n.title}</h3>
            <p className="line-clamp-3 text-xs text-muted">{n.content.replace(/[#*`<>]/g, '').slice(0, 220)}</p>
            <div className="mt-auto flex items-center gap-1 pt-2">
              <button type="button" className="btn-secondary !py-1 !text-xs" onClick={() => onOpen({ id: n.id, title: n.title, type: n.kind === 'html' ? 'html' : 'markdown', content: n.content })}><FileText size={13} /> Open</button>
              <button type="button" className="btn-ghost !p-1.5" aria-label="Download" onClick={() => download(n)}><Download size={15} /></button>
              <button type="button" className="btn-ghost !p-1.5 hover:!text-danger" aria-label="Delete" onClick={() => remove(n.id)}><Trash2 size={15} /></button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
