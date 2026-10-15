import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

export default function ProfileModal({ onClose, personalize, setPersonalize }) {
  const [form, setForm] = useState({ display_name: '', goal: '', background: '', known: '' })
  const [state, setState] = useState('loading')
  const first = useRef(null)

  useEffect(() => {
    api.profile().then((p) => {
      setForm({ display_name: p.display_name || '', goal: p.goal || '', background: p.background || '', known: (p.known_concepts || []).join(', ') })
      setState('ready')
    }).catch(() => setState('error'))
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  useEffect(() => { if (state === 'ready') first.current?.focus() }, [state])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const save = async (e) => {
    e.preventDefault()
    setState('saving')
    try {
      await api.saveProfile({
        display_name: form.display_name, goal: form.goal, background: form.background,
        known_concepts: form.known.split(',').map((s) => s.trim()).filter(Boolean),
      })
      onClose()
    } catch { setState('error') }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/70 p-4 backdrop-blur-sm" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form role="dialog" aria-modal="true" aria-labelledby="profile-title" onSubmit={save} className="card w-full max-w-lg p-5">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 id="profile-title" className="text-2xl font-semibold">Your learner profile</h2>
            <p className="mt-1 text-sm text-muted">Used only to choose analogies and level. Facts always come from the transcripts. Stored in your local database.</p>
          </div>
          <button type="button" className="btn-ghost !p-1.5" aria-label="Close" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="space-y-3">
          <label className="block"><span className="label">Name</span>
            <input ref={first} className="field mt-1" value={form.display_name} onChange={set('display_name')} maxLength={100} /></label>
          <label className="block"><span className="label">Goal</span>
            <input className="field mt-1" value={form.goal} onChange={set('goal')} maxLength={500} placeholder="e.g. Become an AI / forward-deployed engineer" /></label>
          <label className="block"><span className="label">Background</span>
            <textarea className="field mt-1" rows={2} value={form.background} onChange={set('background')} maxLength={1000} placeholder="e.g. Final-year CS student, comfortable with Python and Docker" /></label>
          <label className="block"><span className="label">Concepts I already understand (comma separated)</span>
            <textarea className="field mt-1" rows={2} value={form.known} onChange={set('known')} placeholder="tokens, embeddings, backpropagation, RLHF" /></label>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={personalize} onChange={(e) => setPersonalize(e.target.checked)} className="accent-[rgb(var(--accent))]" />
          Use my profile to tailor answers
        </label>
        {state === 'error' && <p role="alert" className="mt-3 text-sm text-danger">Couldn’t reach the API. Your changes were not saved.</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={state === 'saving' || state === 'loading'}>{state === 'saving' ? 'Saving…' : 'Save profile'}</button>
        </div>
      </form>
    </div>
  )
}
