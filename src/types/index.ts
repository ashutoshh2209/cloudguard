/**
 * CloudGuard domain model.
 *
 * These interfaces are the contract between the UI and the data layer. The mock
 * implementations in `src/api/client.ts` satisfy exactly this shape, so swapping
 * them for `fetch` calls against FastAPI requires no UI changes. Keep these
 * aligned with the server's Pydantic models.
 */

/* -------------------------------------------------------------------------- */
/* Enumerations                                                               */
/* -------------------------------------------------------------------------- */

/** Ordered most→least urgent. `secure` means a check ran and found no problem. */
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'secure'

/** Severities a finding can carry — a finding is never `secure`. */
export type FindingSeverity = Exclude<Severity, 'secure'>

export type FindingStatus = 'open' | 'resolved' | 'suppressed' | 'acknowledged'

export type ServiceId = 's3' | 'ec2' | 'iam' | 'rds' | 'security-group' | 'cloudtrail'

/** A resource's worst open finding, or `secure` when it has none. */
export type ResourceStatus = Severity

export type ScanStatus = 'completed' | 'running' | 'failed' | 'partial'

export type ScanType = 'quick' | 'full'

export type RiskBand = 'critical' | 'high' | 'moderate' | 'low'

/** The four posture domains scored around the security score. */
export type PostureDomain = 'identity' | 'network' | 'storage' | 'monitoring'

/* -------------------------------------------------------------------------- */
/* Findings                                                                   */
/* -------------------------------------------------------------------------- */

/** One row of the "Detected configuration" block on a finding detail view. */
export interface ConfigItem {
  label: string
  value: string
  /** Renders in the critical tone — mark the setting that caused the finding. */
  flagged?: boolean
  /** Short note explaining what the setting controls. */
  hint?: string
}

export interface ComplianceRef {
  framework: string
  control: string
}

/**
 * A node in the finding's configuration diagram — a small left-to-right graph
 * showing how exposure reaches the resource (e.g. Internet → Bucket policy →
 * Objects). Rendered as SVG, not 3D.
 */
export interface ExposurePathNode {
  id: string
  label: string
  sublabel?: string
  /** `threat` sources sit at the left; `target` is the resource itself. */
  kind: 'threat' | 'control' | 'target'
  /** `open` = traffic passes, `blocked` = control stops it. */
  state: 'open' | 'blocked'
}

export interface Finding {
  id: string
  /** Stable rule id, e.g. `S3.PUBLIC_ACCESS`. Maps 1:1 to a backend check. */
  checkId: string
  title: string
  severity: FindingSeverity
  service: ServiceId
  resourceName: string
  /** Id of the matching `CloudResource`, for cross-linking. */
  resourceId: string
  region: string
  /** One-line consequence for the table's summary column. */
  risk: string
  description: string
  /** "Why this matters" — the security impact, in prose. */
  impact: string
  /** Concrete consequences, as bullets. */
  attackPath: string[]
  configuration: ConfigItem[]
  exposurePath: ExposurePathNode[]
  recommendation: string
  remediationSteps: string[]
  /** Illustrative CLI remediation — never executed by the frontend. */
  remediationCli?: string
  compliance: ComplianceRef[]
  /** ISO 8601. */
  detectedAt: string
  status: FindingStatus
  /** ISO 8601 — present when resolved. */
  resolvedAt?: string
  firstSeenInScan: string
  /** Domain this finding scores against. */
  domain: PostureDomain
}

/* -------------------------------------------------------------------------- */
/* Resources                                                                  */
/* -------------------------------------------------------------------------- */

export interface CloudResource {
  id: string
  name: string
  /** Display label, e.g. `S3 Bucket`. */
  type: string
  service: ServiceId
  /** AWS region, or `Global` for IAM and CloudTrail org trails. */
  region: string
  status: ResourceStatus
  openFindings: number
  /** ISO 8601. */
  lastScannedAt: string
  createdAt: string
  /** Rendered as a key/value grid on the resource drawer. */
  metadata: Record<string, string>
  tags: Record<string, string>
  /** Ids of resources this one talks to — drives the infrastructure map. */
  relatedResourceIds: string[]
}

/* -------------------------------------------------------------------------- */
/* Infrastructure graph                                                      */
/* -------------------------------------------------------------------------- */

/** Logical tier, used to lay the graph out left→right / top→bottom. */
export type GraphTier = 'principal' | 'identity' | 'network' | 'compute' | 'data' | 'audit'

export interface GraphNode {
  id: string
  label: string
  sublabel?: string
  service: ServiceId | 'account' | 'user'
  tier: GraphTier
  status: ResourceStatus
  /** Links back to a `CloudResource`, when this node represents one. */
  resourceId?: string
  findings: number
  region: string
  /** Normalised layout position in the range −1…1, y up. */
  position: [number, number, number]
}

export interface GraphEdge {
  id: string
  from: string
  to: string
  /** What the connection represents, shown on hover. */
  relation: string
  /** `exposed` edges are the ones carrying risk — drawn in the severity tone. */
  kind: 'trust' | 'network' | 'data' | 'audit' | 'exposed'
}

export interface InfrastructureGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/* -------------------------------------------------------------------------- */
/* Scans                                                                      */
/* -------------------------------------------------------------------------- */

export interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
  secure: number
}

export interface Scan {
  id: string
  /** ISO 8601 — when the scan started. */
  startedAt: string
  durationSeconds: number
  type: ScanType
  status: ScanStatus
  resourcesScanned: number
  securityScore: number
  counts: SeverityCounts
  services: ServiceId[]
  /** Set when `status` is `failed` or `partial`. */
  note?: string
  triggeredBy: string
}

/* -------------------------------------------------------------------------- */
/* Posture & dashboard                                                        */
/* -------------------------------------------------------------------------- */

export interface DomainScore {
  domain: PostureDomain
  label: string
  score: number
  /** Change against the previous scan. */
  delta: number
  /** Open findings scoring against this domain. */
  openFindings: number
  /** One-line explanation for the tooltip. */
  blurb: string
}

export interface TrendPoint {
  /** Short axis label, e.g. `Aug 22`. */
  label: string
  scanId: string
  score: number
  /** ISO 8601. */
  date: string
  criticalCount: number
  highCount: number
}

export interface SecuritySummary {
  securityScore: number
  /** Point change against the previous scan. */
  scoreDelta: number
  riskBand: RiskBand
  riskLabel: string
  resourcesScanned: number
  totalFindings: number
  counts: SeverityCounts
  /** Checks executed in the latest scan. */
  checksRun: number
  domains: DomainScore[]
  lastScanId: string
  /** ISO 8601. */
  lastScanAt: string
  trend: TrendPoint[]
}

/* -------------------------------------------------------------------------- */
/* Account, workspace & settings                                              */
/* -------------------------------------------------------------------------- */

export interface CloudAccount {
  id: string
  /** Friendly name, e.g. `Production Environment`. */
  name: string
  /** Full 12-digit id. Never render directly — use `maskAccountId()`. */
  accountId: string
  alias: string
  provider: 'aws'
  environment: 'production' | 'staging' | 'development'
  defaultRegion: string
  enabledRegions: string[]
  status: 'connected' | 'disconnected' | 'error' | 'pending'
  /** How CloudGuard would authenticate once a backend exists. */
  accessMethod: string
  roleArn: string
  /** ISO 8601. */
  connectedAt: string
  resourceCount: number
  securityScore: number
}

export interface PolicyRule {
  id: string
  checkId: string
  title: string
  service: ServiceId
  severity: FindingSeverity
  enabled: boolean
  /** Frameworks this rule maps to. */
  frameworks: string[]
  description: string
}

export interface PolicyPack {
  id: string
  name: string
  description: string
  ruleCount: number
  enabledCount: number
  enabled: boolean
  /** e.g. `CIS AWS Foundations Benchmark v3.0`. */
  standard: string
}

export interface ScanPolicyConfig {
  service: ServiceId
  label: string
  description: string
  enabled: boolean
  ruleCount: number
}

export interface NotificationConfig {
  criticalAlerts: boolean
  highAlerts: boolean
  scanCompletion: boolean
  weeklyDigest: boolean
  newResourceDetected: boolean
  email: string
  webhookUrl: string
}

export interface TeamMember {
  id: string
  name: string
  email: string
  role: 'Owner' | 'Security Admin' | 'Engineer' | 'Read-only'
  /** ISO 8601. */
  lastActiveAt: string
  initials: string
}

export interface ApiKeyRecord {
  id: string
  label: string
  /** Already masked — the full value is never held client-side. */
  maskedKey: string
  createdAt: string
  lastUsedAt?: string
  scopes: string[]
}

export interface AppearanceConfig {
  theme: 'dark' | 'light'
  /** Turns off all 3D and non-essential motion. */
  reducedMotion: boolean
  /** Renders the 3D scenes at lower cost. */
  performanceMode: 'auto' | 'high' | 'balanced' | 'off'
  density: 'comfortable' | 'compact'
}

export interface AppSettings {
  scanPolicies: ScanPolicyConfig[]
  notifications: NotificationConfig
  appearance: AppearanceConfig
  defaultScanType: ScanType
  scheduledScans: boolean
  scheduleLabel: string
  team: TeamMember[]
  apiKeys: ApiKeyRecord[]
  policyPacks: PolicyPack[]
}

/* -------------------------------------------------------------------------- */
/* Reports                                                                    */
/* -------------------------------------------------------------------------- */

export interface Report {
  id: string
  title: string
  description: string
  /** Coverage window, e.g. `22 Aug 2026` or `Jul 2026`. */
  period: string
  kind: 'security' | 'monthly' | 'risk' | 'compliance'
  /** ISO 8601. */
  generatedAt: string
  pageCount: number
  highlights: { label: string; value: string }[]
  sections: string[]
  formats: string[]
  /** Frameworks covered — compliance report only. */
  frameworks?: { name: string; passed: number; total: number }[]
}

/* -------------------------------------------------------------------------- */
/* Scan run (the full-screen scan experience)                                 */
/* -------------------------------------------------------------------------- */

export type StageState = 'waiting' | 'running' | 'done' | 'failed'

export interface ScanStage {
  id: string
  label: string
  /** Simulated duration — replaced by real backend progress events. */
  durationMs: number
  /** Present once the stage completes, e.g. `48 resources`. */
  detail?: string
}

export interface ScanStageProgress extends ScanStage {
  state: StageState
}

export type ScanPhase = 'configure' | 'running' | 'complete' | 'error'

export interface ScanRequest {
  services: ServiceId[]
  type: ScanType
  accountId: string
}

/** Payload delivered when a scan finishes. */
export interface ScanResult {
  scan: Scan
  summary: SecuritySummary
  newFindings: number
  resolvedFindings: number
}

/* -------------------------------------------------------------------------- */
/* Shared UI contracts                                                        */
/* -------------------------------------------------------------------------- */

/** Async resource state used by every data hook. */
export interface AsyncState<T> {
  data: T | null
  loading: boolean
  /** True while refetching with data already present — hold the last render. */
  stale: boolean
  error: string | null
}

export interface SortState<K extends string = string> {
  key: K
  direction: 'asc' | 'desc'
}
