# Design

Layout follows Claude's app. Palette: violet (reference: Oogway Labs). Dark is default, with a light variant. Tokens live in `frontend/src/index.css` and `tailwind.config.js`.

## 1. Principles

1. **Trust is visible.** Every claim has a numbered citation; each source opens the video at the right second. Refusals look different from answers.
2. **Honest state.** Status chips, corpus count and model name come from live endpoints, never hard-coded.
3. **Reading first.** Editorial serif (EB Garamond) for headings, Plus Jakarta Sans for UI, generous whitespace.
4. **Chat and artifact side by side.** The artifact never replaces the conversation.
5. **Safe by default.** Untrusted HTML is boxed in and says so.

## 2. Information architecture (Claude-style)

```
Sidebar: logo · + New chat · Chat | Transcripts | Library · Recents (hover to delete) · Profile · status dot · theme
Main:    centred conversation (max 3xl) + one composer          [artifact opens as a right-hand panel]
Composer: text · mode menu (Ask, Explain simply, Quiz me, Ship 30 essay, PRD, Document/HTML) · model picker · send
```
Deliberately removed from the first design: status chips, corpus strip, per-answer metadata, quick-action chips, suggestion cards. Status is one dot (hover for detail); run details sit in the tooltip of an answer's action row and in the API logs.

## 3. Key states

| Surface | States |
|---|---|
| Empty chat | Greeting, centred composer, 3 suggestion pills |
| Sending | Pulsing dots; after 10 s a timer; after 20 s a slow-model note; Stop replaces Send |
| Answer | Serif prose with `[n]` chips; source pills (click to expand excerpt and "Open on YouTube at …") |
| Refusal | One quiet line: not covered by the transcripts |
| Error | Alert with message, hint, Retry; failed message marked "Not sent" |
| Artifact | Right panel: Preview / Code, copy, download, save, close. HTML shows a one-line sandbox notice |
| Library / Transcripts | Loading, empty, error, pagination |

## 4. Responsive behaviour

| Width | Layout |
|---|---|
| ≥ 1024 px | Sidebar + chat; artifact takes about 48% on the right; without one the chat stays centred |
| < 1024 px | Sidebar is a drawer; artifact opens as a full-screen overlay (Esc or X closes) |
| < 768 px | Sidebar becomes a slide-in drawer (menu button) |

## 5. Accessibility

* Skip-to-content link; landmarks (`header`, `nav`, `main`, `aside`); labelled inputs and icon buttons.
* Tabs use `role="tablist"/"tab"` with `aria-selected`; conversation is an `aria-live` region; status uses `role="status"`; errors use `role="alert"`.
* Visible focus ring (amber) on every control; modals close on Esc; citation buttons are real buttons.
* `prefers-reduced-motion` disables animation. Dark and light themes follow the system preference, then the saved choice.
* Contrast follows the system's palette (near-white on deep violet; deep violet on pale lavender); verify with a tool before release.

## 6. Decisions

| Decision | Why |
|---|---|
| Lucide icons and bundled fonts | Work offline for evaluators; no external requests |
| "Ask" sends `mode=auto` | Natural requests ("write an essay about…") still route correctly |
| No auto-send from suggestion cards | The user stays in control of what is sent |
| HTML print not offered | The sandboxed frame is cross-origin; download instead |
| Serif for answers, sans for UI | Reads like long-form text, matches Claude |
