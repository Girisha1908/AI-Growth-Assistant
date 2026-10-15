/** "Starry Night" design system (docs/design.md). Colours are CSS variables so the
 *  same utility classes work in both light and dark themes. */
const c = (name) => `rgb(var(--${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: c('canvas'), surface: c('surface'), raised: c('raised'), line: c('line'),
        ink: c('ink'), muted: c('muted'), accent: c('accent'), 'on-accent': c('on-accent'),
        'accent-soft': c('accent-soft'), 'on-accent-soft': c('on-accent-soft'),
        info: c('info'), danger: c('danger'), ok: c('ok'), trough: c('trough'),
      },
      fontFamily: {
        serif: ['"EB Garamond"', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      borderRadius: { xl: '1rem', '2xl': '1.5rem' },
      boxShadow: {
        card: '0 1px 2px rgb(var(--shadow) / 0.12), 0 8px 24px rgb(var(--shadow) / 0.10)',
      },
    },
  },
  plugins: [],
}
