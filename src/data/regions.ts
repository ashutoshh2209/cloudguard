/** AWS regions CloudGuard sweeps, with display names for the UI. */

export interface RegionMeta {
  id: string
  /** Human label, e.g. `Asia Pacific (Mumbai)`. */
  label: string
  /** Short label for dense table cells, e.g. `Mumbai`. */
  city: string
  geography: string
}

export const REGIONS: RegionMeta[] = [
  {
    id: 'ap-south-1',
    label: 'Asia Pacific (Mumbai)',
    city: 'Mumbai',
    geography: 'Asia Pacific',
  },
  {
    id: 'us-east-1',
    label: 'US East (N. Virginia)',
    city: 'N. Virginia',
    geography: 'Americas',
  },
  { id: 'eu-west-1', label: 'Europe (Ireland)', city: 'Ireland', geography: 'Europe' },
  {
    id: 'ap-southeast-1',
    label: 'Asia Pacific (Singapore)',
    city: 'Singapore',
    geography: 'Asia Pacific',
  },
  { id: 'Global', label: 'Global', city: 'Global', geography: 'Global' },
]

const BY_ID = new Map(REGIONS.map((r) => [r.id, r]))

export function regionMeta(id: string): RegionMeta {
  return BY_ID.get(id) ?? { id, label: id, city: id, geography: 'Unknown' }
}

/** Regions that hold actual resources — excludes the `Global` pseudo-region. */
export const SCANNED_REGIONS = REGIONS.filter((r) => r.id !== 'Global')
