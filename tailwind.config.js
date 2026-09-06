/**
 * CloudGuard — Tailwind theme.
 *
 * Every colour here resolves to a CSS custom property declared in
 * `src/index.css`. That file is the single source of truth for the DOM; the
 * typed mirror used by Three.js and Recharts lives in `src/design/tokens.ts`.
 * Nothing in the app should carry a raw hex value.
 */

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      /* ---------------------------------------------------------------- */
      /* Typography                                                       */
      /* ---------------------------------------------------------------- */
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'Cascadia Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        micro: ['0.6875rem', { lineHeight: '1.25', letterSpacing: '0.06em' }],
        caption: ['0.75rem', { lineHeight: '1.4', letterSpacing: '0.005em' }],
        sm: ['0.8125rem', { lineHeight: '1.5' }],
        base: ['0.875rem', { lineHeight: '1.55' }],
        body: ['1rem', { lineHeight: '1.65' }],
        lead: ['1.125rem', { lineHeight: '1.6', letterSpacing: '-0.005em' }],
        h3: ['1.125rem', { lineHeight: '1.3', letterSpacing: '-0.011em' }],
        h2: ['1.5rem', { lineHeight: '1.22', letterSpacing: '-0.018em' }],
        h1: ['2rem', { lineHeight: '1.14', letterSpacing: '-0.022em' }],
        display: ['3.25rem', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
        'display-lg': ['4.5rem', { lineHeight: '1.0', letterSpacing: '-0.035em' }],
      },

      /* ---------------------------------------------------------------- */
      /* Colour                                                           */
      /* ---------------------------------------------------------------- */
      colors: {
        slate: {
          900: '#172033', // User requested primary slate
        },
        canvas: 'var(--canvas)',
        surface: {
          DEFAULT: 'var(--surface-1)',
          1: 'var(--surface-1)',
          2: 'var(--surface-2)',
          3: 'var(--surface-3)',
          inset: 'var(--surface-inset)',
        },
        line: {
          DEFAULT: 'var(--line)',
          subtle: 'var(--line-subtle)',
          strong: 'var(--line-strong)',
        },
        content: {
          DEFAULT: 'var(--text-1)',
          primary: 'var(--text-1)',
          secondary: 'var(--text-2)',
          tertiary: 'var(--text-3)',
          muted: 'var(--text-4)',
          inverse: 'var(--text-inverse)',
        },
        accent: {
          DEFAULT: 'var(--accent-9)',
          subtle: 'var(--accent-3)',
          border: 'var(--accent-6)',
          9: 'var(--accent-9)',
          10: 'var(--accent-10)',
          11: 'var(--accent-11)',
          12: 'var(--accent-12)',
          3: 'var(--accent-3)',
          6: 'var(--accent-6)',
        },
        /* Severity is a reserved status palette — never used for a data
           series, and never rendered without an accompanying icon + label. */
        severity: {
          critical: 'var(--sev-critical)',
          high: 'var(--sev-high)',
          medium: 'var(--sev-medium)',
          low: 'var(--sev-low)',
          secure: 'var(--sev-secure)',
        },
        'severity-ink': {
          critical: 'var(--sev-critical-ink)',
          high: 'var(--sev-high-ink)',
          medium: 'var(--sev-medium-ink)',
          low: 'var(--sev-low-ink)',
          secure: 'var(--sev-secure-ink)',
        },
        grid: 'var(--grid)',
      },
      borderColor: { DEFAULT: 'var(--line)' },
      ringColor: { DEFAULT: 'var(--accent-9)' },

      /* ---------------------------------------------------------------- */
      /* Depth — surface steps and hairlines do most of the work; shadows  */
      /* stay restrained, with a top inner highlight on raised panels.     */
      /* ---------------------------------------------------------------- */
      boxShadow: {
        e1: 'var(--elev-1)',
        e2: 'var(--elev-2)',
        e3: 'var(--elev-3)',
        e4: 'var(--elev-4)',
        rim: 'var(--rim)',
        'rim-e2': 'var(--rim), var(--elev-2)',
        focus: '0 0 0 2px var(--canvas), 0 0 0 4px var(--accent-9)',
      },

      /* ---------------------------------------------------------------- */
      /* Geometry — tight, technical radii. Nothing pill-shaped.           */
      /* ---------------------------------------------------------------- */
      borderRadius: {
        xs: '3px',
        sm: '4px',
        DEFAULT: '6px',
        md: '6px',
        lg: '8px',
        xl: '10px',
        '2xl': '14px',
      },
      spacing: {
        sidebar: '15rem',
        'sidebar-sm': '3.5rem',
        topbar: '3.5rem',
      },
      maxWidth: {
        prose: '68ch',
        shell: '96rem',
        marketing: '75rem',
      },

      /* ---------------------------------------------------------------- */
      /* Motion — intentional, short, and never looping in the background  */
      /* ---------------------------------------------------------------- */
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        entrance: 'cubic-bezier(0.16, 1, 0.3, 1)',
        exit: 'cubic-bezier(0.4, 0, 1, 1)',
      },
      transitionDuration: {
        fast: '120ms',
        base: '180ms',
        slow: '280ms',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'rise-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.98)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'drawer-in': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        sweep: { '100%': { transform: 'translateX(100%)' } },
        'pulse-ring': {
          '0%': { opacity: '0.5', transform: 'scale(1)' },
          '70%, 100%': { opacity: '0', transform: 'scale(2.2)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 180ms cubic-bezier(0.2, 0, 0, 1) both',
        'rise-in': 'rise-in 220ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'scale-in': 'scale-in 160ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'drawer-in': 'drawer-in 280ms cubic-bezier(0.32, 0.72, 0, 1) both',
        sweep: 'sweep 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite',
        'pulse-ring': 'pulse-ring 2.4s cubic-bezier(0.2, 0, 0, 1) infinite',
      },
      zIndex: {
        sticky: '20',
        drawer: '40',
        modal: '50',
        toast: '60',
        tooltip: '70',
      },
    },
  },
  plugins: [],
}
