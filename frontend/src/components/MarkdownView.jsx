import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { linkCitations } from '../lib/text'

/**
 * Renders model Markdown safely. Raw HTML inside Markdown (e.g. quiz <details>) is
 * parsed by rehype-raw and then ALWAYS passed through rehype-sanitize (GitHub-style
 * allow-list): no <script>, no event handlers, no javascript: URLs.
 */
const SCHEMA = { ...defaultSchema }

export function renderLink(onCite) {
  return function Link({ href, children, ...rest }) {
    const m = /^#(?:user-content-)?cite-(\d+)$/.exec(href || '')
    if (m) {
      const n = Number(m[1])
      return (
        <button type="button" className="cite" aria-label={`Source ${n}`} onClick={() => onCite?.(n)}>
          {n}
        </button>
      )
    }
    return <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>
  }
}

export default function MarkdownView({ text, sourceCount = 0, onCite, className = '' }) {
  return (
    <div className={`prose-lga ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, SCHEMA]]}
        components={{ a: renderLink(onCite) }}
      >
        {linkCitations(text, sourceCount)}
      </ReactMarkdown>
    </div>
  )
}
