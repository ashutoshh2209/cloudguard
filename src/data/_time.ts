/**
 * Shared clock for the mock dataset.
 *
 * Timestamps are generated as offsets from module load, so "12 min ago" reads
 * correctly whenever the app is opened rather than drifting into "8 months ago".
 * Once the FastAPI backend supplies real timestamps this file goes away.
 */

/** Captured once at module load so every mock record shares one reference point. */
export const NOW = new Date()

export const minutesAgo = (n: number): string =>
  new Date(NOW.getTime() - n * 60_000).toISOString()

export const hoursAgo = (n: number): string => minutesAgo(n * 60)

export const daysAgo = (n: number): string => minutesAgo(n * 60 * 24)
