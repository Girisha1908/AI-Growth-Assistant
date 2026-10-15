import { ShieldCheck } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { buildSrcDoc, sandboxAttr } from '../lib/sandbox'

/** Renders UNTRUSTED model HTML. See lib/sandbox.js for exactly what is permitted/blocked. */
export default function HtmlSandbox({ html, title }) {
  const [allowScripts, setAllowScripts] = useState(false)

  const { srcDoc, error } = useMemo(() => {
    try {
      return { srcDoc: buildSrcDoc(html, { allowScripts }), error: null }
    } catch (e) {
      api.reportClientEvent('artifact_render_error', String(e.message || e).slice(0, 300), { bytes: html.length })
      return { srcDoc: '', error: e }
    }
  }, [html, allowScripts])

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-raised px-3 py-1.5 text-xs text-muted">
        <span className="flex items-center gap-1.5"><ShieldCheck size={14} className="text-ok" aria-hidden />
          Sandboxed: no network, cookies, popups or navigation{allowScripts ? '' : ', scripts off'}.
        </span>
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={allowScripts} className="accent-[rgb(var(--accent))]"
            onChange={(e) => setAllowScripts(e.target.checked)} />
          Allow scripts (still isolated)
        </label>
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-danger/50 bg-danger/10 p-3 text-sm text-danger">
          This artifact couldn’t be rendered safely. The error was reported to the API logs. Use the Source view instead.
        </p>
      ) : (
        <iframe key={String(allowScripts)} title={`Artifact preview: ${title}`} srcDoc={srcDoc}
          sandbox={sandboxAttr(allowScripts)} referrerPolicy="no-referrer"
          className="min-h-0 w-full flex-1 rounded-lg border border-line bg-white" />
      )}
    </div>
  )
}
