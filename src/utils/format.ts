/* Formatting helpers. All timestamps in the app are ISO 8601 strings. */

/**
 * Compact relative time, e.g. `12 min ago`, `3 hr ago`, `2 days ago`.
 * `now` is injectable so the value is deterministic in tests.
 */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'

  const diffMs = now.getTime() - then
  const future = diffMs < 0
  const seconds = Math.floor(Math.abs(diffMs) / 1000)

  const phrase = ((): string => {
    if (seconds < 45) return 'just now'
    if (seconds < 90) return '1 min'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} min`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} hr`
    const days = Math.floor(hours / 24)
    if (days === 1) return '1 day'
    if (days < 30) return `${days} days`
    const months = Math.floor(days / 30)
    if (months === 1) return '1 month'
    if (months < 12) return `${months} months`
    const years = Math.floor(months / 12)
    return years === 1 ? '1 year' : `${years} years`
  })()

  if (phrase === 'just now') return phrase
  return future ? `in ${phrase}` : `${phrase} ago`
}

/** `22 Aug 2026` */
export function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/** `22 Aug 2026, 14:32` */
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return `${formatDate(iso)}, ${d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

/** `Aug 2026` — for monthly report periods. */
export function formatMonth(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })
}

/** `1m 48s` / `52s` */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest === 0 ? `${mins}m` : `${mins}m ${rest}s`
}

/**
 * Masks all but the last four digits of an AWS account id:
 * `918273645500` → `•••• •••• 5500`.
 */
export function maskAccountId(accountId: string): string {
  const tail = accountId.slice(-4)
  return `•••• •••• ${tail}`
}

/** Signed delta for a stat tile, e.g. `+8`, `-3`, `0`. */
export function signedDelta(value: number): string {
  if (value === 0) return '0'
  return value > 0 ? `+${value}` : `${value}`
}

/** Compact counts: `1,284` → `1,284`; `12900` → `12.9K`. */
export function compactNumber(value: number): string {
  if (Math.abs(value) < 10_000) return value.toLocaleString('en-US')
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

/** Sentence-case a slug: `security-group` → `Security group`. */
export function humanize(slug: string): string {
  const spaced = slug.replace(/[-_]/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

/** Case-insensitive substring match across several fields. */
export function matchesQuery(query: string, ...fields: (string | undefined)[]): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return fields.some((f) => f?.toLowerCase().includes(q))
}

/** Inclusive day-window filter used by the date range dropdowns. */
export function withinDays(iso: string, days: number, now: Date = new Date()): boolean {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return false
  return now.getTime() - then <= days * 24 * 60 * 60 * 1000
}
