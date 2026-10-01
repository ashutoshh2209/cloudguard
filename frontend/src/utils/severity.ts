import type {
  FindingStatus,
  PostureDomain,
  RiskBand,
  ServiceId,
  Severity,
} from '@/types'
import { SEVERITY_COLOR, SEVERITY_INK } from '@/design/tokens'

/* ==========================================================================
   Severity
   The status palette is reserved: these colours mean state, never series
   identity, and they are never rendered without an accompanying label (and,
   in badges, an icon). Amber and yellow are the closest pair in the ramp, so
   the label is what actually separates High from Medium — not the hue.
   ========================================================================== */

export interface SeverityMeta {
  id: Severity
  /** Badge text, e.g. `CRITICAL`. */
  label: string
  /** Sentence case, for prose and legends. */
  name: string
  /** Zero-padded count used in the findings summary strip, e.g. `03`. */
  hex: string
  /** Tailwind: solid badge. */
  badge: string
  /** Tailwind: quiet chip — tinted background, hairline ring, ink text. */
  chip: string
  /** Tailwind: text in the severity tone (uses the darkened ink step). */
  text: string
  /** Tailwind: 6px status dot. */
  dot: string
  /** Tailwind: left rail on table rows and detail headers. */
  rail: string
  /** Tailwind: tinted fill for meters and heat cells. */
  fill: string
  /** Higher = more urgent. Drives sorts. */
  weight: number
}

export const SEVERITY_META: Record<Severity, SeverityMeta> = {
  critical: {
    id: 'critical',
    label: 'CRITICAL',
    name: 'Critical',
    hex: SEVERITY_COLOR.critical,
    badge: 'bg-severity-critical text-white',
    chip: 'bg-severity-critical/12 text-severity-ink-critical ring-1 ring-inset ring-severity-critical/30',
    text: 'text-severity-ink-critical',
    dot: 'bg-severity-critical',
    rail: 'border-l-severity-critical',
    fill: 'bg-severity-critical',
    weight: 5,
  },
  high: {
    id: 'high',
    label: 'HIGH',
    name: 'High',
    hex: SEVERITY_COLOR.high,
    badge: 'bg-severity-high text-[#241202]',
    chip: 'bg-severity-high/12 text-severity-ink-high ring-1 ring-inset ring-severity-high/30',
    text: 'text-severity-ink-high',
    dot: 'bg-severity-high',
    rail: 'border-l-severity-high',
    fill: 'bg-severity-high',
    weight: 4,
  },
  medium: {
    id: 'medium',
    label: 'MEDIUM',
    name: 'Medium',
    hex: SEVERITY_COLOR.medium,
    badge: 'bg-severity-medium text-[#2a2103]',
    chip: 'bg-severity-medium/12 text-severity-ink-medium ring-1 ring-inset ring-severity-medium/30',
    text: 'text-severity-ink-medium',
    dot: 'bg-severity-medium',
    rail: 'border-l-severity-medium',
    fill: 'bg-severity-medium',
    weight: 3,
  },
  low: {
    id: 'low',
    label: 'LOW',
    name: 'Low',
    hex: SEVERITY_COLOR.low,
    badge: 'bg-severity-low text-[#0b1017]',
    chip: 'bg-severity-low/14 text-severity-ink-low ring-1 ring-inset ring-severity-low/30',
    text: 'text-severity-ink-low',
    dot: 'bg-severity-low',
    rail: 'border-l-severity-low',
    fill: 'bg-severity-low',
    weight: 2,
  },
  secure: {
    id: 'secure',
    label: 'SECURE',
    name: 'Secure',
    hex: SEVERITY_COLOR.secure,
    badge: 'bg-severity-secure text-white',
    chip: 'bg-severity-secure/12 text-severity-ink-secure ring-1 ring-inset ring-severity-secure/30',
    text: 'text-severity-ink-secure',
    dot: 'bg-severity-secure',
    rail: 'border-l-severity-secure',
    fill: 'bg-severity-secure',
    weight: 1,
  },
}

/** Canonical order for tabs, legends, summary strips and sorts. */
export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'secure']

/** Severities a finding can carry. */
export const FINDING_SEVERITIES = ['critical', 'high', 'medium', 'low'] as const

/** Mark colour for a chart or 3D material. Identical across themes. */
export function severityColor(severity: Severity): string {
  return SEVERITY_COLOR[severity]
}

/** Text-safe colour for the active theme. */
export function severityInk(severity: Severity, theme: 'dark' | 'light'): string {
  return SEVERITY_INK[theme][severity]
}

/** The worst severity in a list, or `secure` when the list is empty. */
export function worstSeverity(severities: Severity[]): Severity {
  return severities.reduce<Severity>(
    (worst, s) => (SEVERITY_META[s].weight > SEVERITY_META[worst].weight ? s : worst),
    'secure',
  )
}

/** Zero-pad a count for the summary strip: 3 → `03`. */
export function padCount(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

/* ==========================================================================
   Risk bands
   ========================================================================== */

export interface RiskBandMeta {
  band: RiskBand
  label: string
  severity: Severity
  /** Plain-language explanation for the score tooltip. */
  blurb: string
}

const RISK_BANDS: RiskBandMeta[] = [
  {
    band: 'critical',
    label: 'Critical Risk',
    severity: 'critical',
    blurb: 'Severe exposure. Treat open critical findings as an active incident.',
  },
  {
    band: 'high',
    label: 'High Risk',
    severity: 'high',
    blurb: 'Multiple exploitable misconfigurations. Remediate before further deploys.',
  },
  {
    band: 'moderate',
    label: 'Moderate Risk',
    severity: 'medium',
    blurb: 'Core controls are in place, but notable gaps remain in this account.',
  },
  {
    band: 'low',
    label: 'Low Risk',
    severity: 'secure',
    blurb: 'Configuration is broadly aligned with cloud security best practice.',
  },
]

/** Thresholds: <40 critical · <60 high · <85 moderate · else low. */
export function riskBandForScore(score: number): RiskBandMeta {
  if (score < 40) return RISK_BANDS[0]
  if (score < 60) return RISK_BANDS[1]
  if (score < 85) return RISK_BANDS[2]
  return RISK_BANDS[3]
}

export function riskBandMeta(band: RiskBand): RiskBandMeta {
  return RISK_BANDS.find((b) => b.band === band) ?? RISK_BANDS[2]
}

/* ==========================================================================
   Services
   ========================================================================== */

export interface ServiceMeta {
  id: ServiceId
  /** Table/badge label, e.g. `S3`. */
  short: string
  /** Full product name, e.g. `Amazon S3`. */
  full: string
  /** Plural noun for counts, e.g. `buckets`. */
  unit: string
  /** What CloudGuard inspects. */
  scope: string
  /** Posture domain this service scores against. */
  domain: PostureDomain
}

export const SERVICE_META: Record<ServiceId, ServiceMeta> = {
  s3: {
    id: 's3',
    short: 'S3',
    full: 'Amazon S3',
    unit: 'buckets',
    scope: 'Bucket policies, ACLs, encryption, versioning and access logging',
    domain: 'storage',
  },
  ec2: {
    id: 'ec2',
    short: 'EC2',
    full: 'Amazon EC2',
    unit: 'instances',
    scope: 'Public addressing, EBS encryption, IMDS version and instance profiles',
    domain: 'network',
  },
  iam: {
    id: 'iam',
    short: 'IAM',
    full: 'AWS IAM',
    unit: 'identities',
    scope: 'Users, roles, policies, MFA, key age and privilege scope',
    domain: 'identity',
  },
  rds: {
    id: 'rds',
    short: 'RDS',
    full: 'Amazon RDS',
    unit: 'databases',
    scope: 'Public accessibility, encryption at rest, backups and patch level',
    domain: 'storage',
  },
  'security-group': {
    id: 'security-group',
    short: 'SG',
    full: 'Security Groups',
    unit: 'groups',
    scope: 'Inbound and outbound rules, open ports and source CIDR ranges',
    domain: 'network',
  },
  cloudtrail: {
    id: 'cloudtrail',
    short: 'CloudTrail',
    full: 'AWS CloudTrail',
    unit: 'trails',
    scope: 'Trail coverage, log file validation and multi-region delivery',
    domain: 'monitoring',
  },
}

/** Display order for service filters, cards and legends. */
export const SERVICE_ORDER: ServiceId[] = [
  's3',
  'ec2',
  'iam',
  'rds',
  'security-group',
  'cloudtrail',
]

/* ==========================================================================
   Posture domains
   ========================================================================== */

export const DOMAIN_LABEL: Record<PostureDomain, string> = {
  identity: 'Identity',
  network: 'Network',
  storage: 'Storage',
  monitoring: 'Monitoring',
}

export const DOMAIN_ORDER: PostureDomain[] = ['identity', 'network', 'storage', 'monitoring']

/* ==========================================================================
   Finding status
   Neutral chrome by design — a status colour here would compete with the
   severity badge in the same row. State reads from the label.
   ========================================================================== */

export const FINDING_STATUS_META: Record<
  FindingStatus,
  { label: string; chip: string }
> = {
  open: {
    label: 'Open',
    chip: 'bg-surface-3 text-content-secondary ring-1 ring-inset ring-line-strong',
  },
  acknowledged: {
    label: 'Acknowledged',
    chip: 'bg-surface-3 text-content-secondary ring-1 ring-inset ring-line-strong',
  },
  resolved: {
    label: 'Resolved',
    chip: 'bg-severity-secure/10 text-severity-ink-secure ring-1 ring-inset ring-severity-secure/28',
  },
  suppressed: {
    label: 'Suppressed',
    chip: 'bg-surface-3 text-content-muted ring-1 ring-inset ring-line',
  },
}
