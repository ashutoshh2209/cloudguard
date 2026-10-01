/**
 * Typed token mirror.
 *
 * `src/index.css` is the source of truth for the DOM. Three.js and Recharts
 * cannot read Tailwind classes, so they read from here. These values MUST match
 * the corresponding custom properties in index.css — if you change one, change
 * both. For anything that must react to a live theme switch, prefer
 * `readCssVar()` over the constants below.
 */

import type { Severity } from '@/types'

export type ThemeName = 'dark' | 'light'

/* -------------------------------------------------------------------------- */
/* Planes & ink                                                               */
/* -------------------------------------------------------------------------- */

export const PLANES = {
  dark: {
    canvas: '#08090b',
    surface1: '#0e1014',
    surface2: '#13161b',
    surface3: '#1a1e25',
    line: 'rgba(255,255,255,0.09)',
    text1: '#e7eaf0',
    text2: '#99a2b0',
    text3: '#6d7684',
    grid: 'rgba(255,255,255,0.055)',
  },
  light: {
    canvas: '#f7f8fa',
    surface1: '#ffffff',
    surface2: '#fbfbfd',
    surface3: '#f1f3f7',
    line: 'rgba(11,15,25,0.11)',
    text1: '#0c1017',
    text2: '#4e5866',
    text3: '#6c7686',
    grid: 'rgba(11,15,25,0.07)',
  },
} as const satisfies Record<ThemeName, Record<string, string>>

export const ACCENT = {
  dark: { base: '#4a6cf7', bright: '#5a7afa', text: '#8ea8fd', pale: '#d6e0ff' },
  light: { base: '#3453d9', bright: '#2a45bd', text: '#2c47c4', pale: '#16224f' },
} as const satisfies Record<ThemeName, Record<string, string>>

/* -------------------------------------------------------------------------- */
/* Severity — identical in both themes so a colour never changes meaning      */
/* -------------------------------------------------------------------------- */

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: '#e5484d',
  high: '#f08a24',
  medium: '#e5c158',
  low: '#7e90a8',
  secure: '#33a06b',
}

/** Text-safe steps. Amber/yellow need darkening on a light plane. */
export const SEVERITY_INK: Record<ThemeName, Record<Severity, string>> = {
  dark: {
    critical: '#f2777b',
    high: '#f6a45b',
    medium: '#e5c158',
    low: '#93a3b8',
    secure: '#4cba85',
  },
  light: {
    critical: '#b62328',
    high: '#9a5308',
    medium: '#7d6410',
    low: '#566579',
    secure: '#16744a',
  },
}

/* -------------------------------------------------------------------------- */
/* Motion                                                                     */
/* -------------------------------------------------------------------------- */

export const DURATION = {
  fast: 0.12,
  base: 0.18,
  slow: 0.28,
  page: 0.34,
} as const

/** Framer Motion easing curves matched to the CSS timing functions. */
export const EASE = {
  standard: [0.2, 0, 0, 1],
  entrance: [0.16, 1, 0.3, 1],
  exit: [0.4, 0, 1, 1],
} as const

/** Spring presets. `firm` for UI feedback, `soft` for camera and layout. */
export const SPRING = {
  firm: { type: 'spring', stiffness: 420, damping: 34, mass: 0.9 },
  soft: { type: 'spring', stiffness: 190, damping: 26, mass: 1 },
  gentle: { type: 'spring', stiffness: 120, damping: 22, mass: 1.1 },
} as const

/* -------------------------------------------------------------------------- */
/* Runtime access                                                             */
/* -------------------------------------------------------------------------- */

/** Read a live custom property — use when a value must follow a theme switch. */
export function readCssVar(name: string, fallback = ''): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/** The theme currently stamped on `<html>`. */
export function currentTheme(): ThemeName {
  if (typeof document === 'undefined') return 'dark'
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
}

/** Chart chrome resolved for a theme — axis ink, gridlines, tooltip surface. */
export function chartChrome(theme: ThemeName) {
  const p = PLANES[theme]
  return {
    axis: p.text3,
    grid: theme === 'dark' ? 'rgba(255,255,255,0.07)' : 'rgba(11,15,25,0.08)',
    tooltipBg: theme === 'dark' ? '#13161b' : '#ffffff',
    tooltipBorder: p.line,
    label: p.text2,
  }
}
