import { Menu, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import ArtifactPanel from './components/ArtifactPanel'
import Composer from './components/Composer'
import LibraryTab from './components/LibraryTab'
import MessageList from './components/MessageList'
import ProfileModal from './components/ProfileModal'
import Sidebar from './components/Sidebar'
import TranscriptsTab from './components/TranscriptsTab'
import { useChat } from './hooks/useChat'
import { useStatus } from './hooks/useStatus'
import { useTheme } from './hooks/useTheme'

const IDEAS = [
  { mode: 'ask', label: 'Improve user retention', text: 'How should product teams approach improving user retention?' },
  { mode: 'explain', label: 'Explain product-market fit', text: 'What is product-market fit?' },
  { mode: 'ship30', label: 'Write a Ship 30 essay', text: 'Why retention beats acquisition' },
]

export default function App() {
  const { theme, toggle } = useTheme()
  const status = useStatus()
  const [tab, setTab] = useState('chat')
  const [artifact, setArtifact] = useState(null)
  const [mode, setMode] = useState('ask')
  const [text, setText] = useState('')
  const [provider, setProvider] = useState('')
  const [personalize, setPersonalize] = useState(() => {
    try { return localStorage.getItem('lga-personalize') !== 'false' } catch { return true }
  })
  const [libraryKey, setLibraryKey] = useState(0)
  const [profileOpen, setProfileOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const chat = useChat({ onArtifact: setArtifact })

  useEffect(() => {
    try { localStorage.setItem('lga-personalize', String(personalize)) } catch { /* ignore */ }
  }, [personalize])

  const handleSend = () => {
    const t = text
    setText('')
    // "Ask" sends mode=auto so natural requests ("write a Ship 30 essay…") still route correctly.
    chat.send({ text: t, mode: mode === 'ask' ? 'auto' : mode, provider, personalize })
  }

  const pick = useCallback((m, t) => { setMode(m); setText(t); setTab('chat') }, [])
  const newChat = () => { chat.newChat(); setArtifact(null); setTab('chat') }
  const selectSession = (id) => { setArtifact(null); setTab('chat'); chat.loadSession(id) }
  const openArtifact = (a) => { setArtifact(a); setTab('chat') }
  const bumpLibrary = () => setLibraryKey((k) => k + 1)

  const empty = chat.messages.length === 0 && !chat.sending
  const composer = (
    <Composer sending={chat.sending} onSend={handleSend} onStop={chat.stop} config={status.config}
      mode={mode} setMode={setMode} text={text} setText={setText}
      provider={provider} setProvider={setProvider} autoFocus={tab === 'chat'} />
  )
  const title = chat.messages.find((m) => m.role === 'user')?.content

  return (
    <div className="flex h-full">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-accent focus:px-3 focus:py-1 focus:text-on-accent">Skip to content</a>
      <Sidebar tab={tab} setTab={setTab} theme={theme} onToggleTheme={toggle} onNewChat={newChat}
        onOpenProfile={() => setProfileOpen(true)} onSelectSession={selectSession}
        activeSessionId={chat.sessionId} refreshKey={`${chat.sessionId}-${chat.messages.length}`}
        status={status} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-w-0 flex-1">
        <main id="main" className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-2 px-3 py-2.5 lg:hidden">
            <button type="button" className="btn-ghost !p-2" aria-label="Open sidebar" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
            <span className="truncate text-sm font-medium text-muted">{tab === 'chat' ? title || 'New chat' : tab === 'transcripts' ? 'Transcripts' : 'Library'}</span>
          </div>

          {tab === 'chat' && (empty ? (
            <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 pb-16">
              <h1 className="mb-8 flex items-center gap-3 text-center text-4xl font-medium tracking-tight sm:text-5xl">
                <Sparkles className="shrink-0 text-accent" size={34} aria-hidden /> How can I help you learn today?
              </h1>
              <div className="w-full max-w-2xl">{composer}</div>
              <ul className="mt-4 flex max-w-2xl flex-wrap justify-center gap-2">
                {IDEAS.map((i) => (
                  <li key={i.label}>
                    <button type="button" onClick={() => pick(i.mode, i.text)}
                      className="rounded-full border border-line px-4 py-1.5 text-sm text-muted transition hover:border-accent/60 hover:text-ink">{i.label}</button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <>
              <div className="min-h-0 flex-1 overflow-y-auto">
                <div className="mx-auto w-full max-w-3xl px-4 py-8">
                  <MessageList messages={chat.messages} sending={chat.sending} sendingMode={mode} error={chat.error}
                    onRetry={chat.retry} onOpenArtifact={setArtifact} onSaved={bumpLibrary} />
                </div>
              </div>
              <div className="mx-auto w-full max-w-3xl px-4 pb-4">{composer}</div>
            </>
          ))}

          {tab === 'transcripts' && <div className="min-h-0 flex-1 overflow-y-auto"><TranscriptsTab onAsk={(t) => pick('ask', t)} /></div>}
          {tab === 'library' && <div className="min-h-0 flex-1 overflow-y-auto"><LibraryTab onOpen={openArtifact} refreshKey={libraryKey} /></div>}
        </main>

        {artifact && tab === 'chat' && (
          <div className="fixed inset-0 z-40 bg-canvas lg:static lg:z-auto lg:w-[48%] lg:max-w-[780px] lg:border-l lg:border-line">
            <ArtifactPanel artifact={artifact} onClose={() => setArtifact(null)} onSaved={bumpLibrary} />
          </div>
        )}
      </div>

      {profileOpen && <ProfileModal onClose={() => setProfileOpen(false)} personalize={personalize} setPersonalize={setPersonalize} />}
    </div>
  )
}
