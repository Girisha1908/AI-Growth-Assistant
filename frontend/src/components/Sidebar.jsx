import { BookOpen, Library, MessageSquare, Moon, Plus, Sparkles, Sun, Trash2, User, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const NAV = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'transcripts', label: 'Transcripts', icon: BookOpen },
  { id: 'library', label: 'Library', icon: Library },
]

function statusInfo(status) {
  if (status.unreachable) return ['bg-danger', 'API offline']
  const h = status.health
  if (!h) return ['bg-muted', 'Connecting…']
  const p = h.provider_detail
  if (h.status === 'ok') return ['bg-ok', `Ready · ${p.name}${p.model ? ` · ${p.model}` : ''}`]
  return ['bg-danger', h.database !== 'connected' ? 'Database unreachable' : `${p?.name || 'Model'} unreachable. Is Ollama running?`]
}

export default function Sidebar({ tab, setTab, theme, onToggleTheme, onNewChat, onOpenProfile, onSelectSession,
  activeSessionId, refreshKey, status, open, onClose }) {
  const [rows, setRows] = useState([])
  useEffect(() => { api.sessions().then(setRows).catch(() => {}) }, [refreshKey])
  const [dot, label] = statusInfo(status)

  const remove = async (e, id) => {
    e.stopPropagation()
    await api.deleteSession(id).catch(() => {})
    setRows((r) => r.filter((x) => x.id !== id))
    if (id === activeSessionId) onNewChat()
  }

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={onClose} aria-hidden />}
      <aside aria-label="Sidebar"
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line/60 bg-trough transition-transform lg:static lg:z-auto lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between px-4 pb-2 pt-4">
          <div className="flex items-center gap-2 font-serif text-xl font-semibold">
            <Sparkles size={18} className="text-accent" aria-hidden /> Lenny Assistant
          </div>
          <button type="button" className="btn-ghost !p-1.5 lg:hidden" aria-label="Close sidebar" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="px-3 pt-2">
          <button type="button" onClick={() => { onNewChat(); onClose() }}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-accent transition hover:bg-raised">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-on-accent"><Plus size={14} /></span> New chat
          </button>
          <nav aria-label="Sections" className="mt-1 space-y-0.5">
            {NAV.map(({ id, label: l, icon: Icon }) => (
              <button key={id} type="button" aria-current={tab === id ? 'page' : undefined}
                onClick={() => { setTab(id); onClose() }}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${tab === id ? 'bg-raised font-semibold text-ink' : 'text-muted hover:bg-raised/60 hover:text-ink'}`}>
                <Icon size={17} aria-hidden /> {l}
              </button>
            ))}
          </nav>
        </div>

        <p className="label mt-5 px-6">Recents</p>
        <ul className="mt-1 min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3">
          {rows.length === 0 && <li className="px-3 py-2 text-sm text-muted">No chats yet</li>}
          {rows.map((s) => (
            <li key={s.id}>
              <div role="button" tabIndex={0} onClick={() => { onSelectSession(s.id); onClose() }}
                onKeyDown={(e) => e.key === 'Enter' && onSelectSession(s.id)}
                className={`group flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm ${s.id === activeSessionId && tab === 'chat' ? 'bg-raised text-ink' : 'text-muted hover:bg-raised/60 hover:text-ink'}`}>
                <span className="truncate">{s.title}</span>
                <button type="button" aria-label="Delete chat" onClick={(e) => remove(e, s.id)}
                  className="rounded p-1 opacity-0 hover:text-danger focus:opacity-100 group-hover:opacity-100"><Trash2 size={14} /></button>
              </div>
            </li>
          ))}
        </ul>

        <div className="flex items-center justify-between border-t border-line/60 px-3 py-3">
          <button type="button" onClick={onOpenProfile} className="flex min-w-0 items-center gap-2 rounded-xl px-2 py-1.5 text-sm hover:bg-raised">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-on-accent-soft"><User size={16} /></span>
            <span className="truncate font-medium">Profile</span>
          </button>
          <div className="flex items-center gap-1">
            <span role="status" aria-label={label} title={label} className="flex h-8 w-8 items-center justify-center">
              <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
            </span>
            <button type="button" className="btn-ghost !p-2" aria-label="Toggle light or dark theme" onClick={onToggleTheme}>
              {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
