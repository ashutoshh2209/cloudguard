import type { CloudResource, ResourceStatus, ServiceId } from '@/types'
import { daysAgo, minutesAgo } from './_time'

/**
 * Resource inventory for the Production Environment account: 48 resources.
 *
 * Fixed composition — S3 12 · EC2 18 · IAM 9 · RDS 2 · Security Groups 7.
 * `status` is always the worst open finding on the resource, and `openFindings`
 * must agree with `findings.ts`; `assertInventory()` enforces both at import.
 */

/** Every resource was swept by the most recent scan. */
const SCANNED = minutesAgo(12)

interface Seed {
  name: string
  region: string
  status: ResourceStatus
  openFindings: number
  ageDays: number
  metadata: Record<string, string>
  tags?: Record<string, string>
  /**
   * Related resources written as **names**, not ids — ids are generated from
   * array position, so referencing them by hand silently rots the moment a
   * seed moves. `resolveRelations()` converts these to ids at module load and
   * throws on a typo.
   */
  related?: string[]
}

function build(
  service: ServiceId,
  type: string,
  idPrefix: string,
  seeds: Seed[],
): CloudResource[] {
  return seeds.map((s, i) => ({
    id: `${idPrefix}-${String(i + 1).padStart(2, '0')}`,
    name: s.name,
    type,
    service,
    region: s.region,
    status: s.status,
    openFindings: s.openFindings,
    lastScannedAt: SCANNED,
    createdAt: daysAgo(s.ageDays),
    metadata: s.metadata,
    tags: s.tags ?? { Environment: 'production', ManagedBy: 'terraform' },
    // Holds names until resolveRelations() rewrites them below.
    relatedResourceIds: s.related ?? [],
  }))
}

/* -------------------------------------------------------------------------- */
/* S3 — 12 buckets                                                            */
/* -------------------------------------------------------------------------- */

const S3 = build('s3', 'S3 Bucket', 's3', [
  {
    name: 'college-project-data',
    region: 'ap-south-1',
    status: 'critical',
    openFindings: 2,
    ageDays: 61,
    metadata: {
      Objects: '1,284',
      Size: '3.2 GB',
      Encryption: 'SSE-S3 (AES-256)',
      'Block Public Access': 'Disabled',
      'Bucket ACL': 'public-read',
      Versioning: 'Disabled',
      'Access logging': 'Disabled',
    },
    tags: { Environment: 'production', Owner: 'data-platform', ManagedBy: 'console' },
  },
  {
    name: 'cg-user-uploads',
    region: 'ap-south-1',
    status: 'high',
    openFindings: 1,
    ageDays: 154,
    metadata: {
      Objects: '48,910',
      Size: '61.4 GB',
      Encryption: 'None',
      'Block Public Access': 'Enabled',
      Versioning: 'Enabled',
    },
  },
  {
    name: 'cg-prod-assets',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 288,
    metadata: {
      Objects: '12,447',
      Size: '18.9 GB',
      Encryption: 'SSE-KMS (aws/s3)',
      'Block Public Access': 'Enabled',
      'Access logging': 'Disabled',
    },
  },
  {
    name: 'cg-invoice-pdfs',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 203,
    metadata: {
      Objects: '9,038',
      Size: '4.1 GB',
      Encryption: 'SSE-KMS (alias/cg-finance)',
      'Bucket policy': 'No aws:SecureTransport condition',
    },
    tags: { Environment: 'production', Owner: 'finance', Compliance: 'pci' },
  },
  {
    name: 'cg-temp-scratch',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 27,
    metadata: {
      Objects: '204,551',
      Size: '412 GB',
      Encryption: 'SSE-S3 (AES-256)',
      'Lifecycle rules': 'None',
    },
    tags: { Environment: 'production', Owner: 'unassigned', ManagedBy: 'console' },
  },
  {
    name: 'cg-analytics-exports',
    region: 'us-east-1',
    status: 'low',
    openFindings: 1,
    ageDays: 175,
    metadata: {
      Objects: '31,204',
      Size: '124 GB',
      Encryption: 'SSE-KMS (alias/cg-analytics)',
      'Storage class': 'Standard',
    },
  },
  {
    name: 'cg-prod-logs-ap-south-1',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 288,
    metadata: {
      Objects: '882,441',
      Size: '1.4 TB',
      Encryption: 'SSE-KMS (alias/cg-logs)',
      'Object Lock': 'Governance, 90 days',
    },
  },
  {
    name: 'cg-cloudtrail-archive',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 288,
    metadata: {
      Objects: '204,118',
      Size: '96.2 GB',
      Encryption: 'SSE-KMS (alias/cg-audit)',
      'Object Lock': 'Compliance, 365 days',
    },
    tags: { Environment: 'production', Owner: 'security', Compliance: 'cis' },
  },
  {
    name: 'cg-terraform-state',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 301,
    metadata: {
      Objects: '412',
      Size: '84 MB',
      Encryption: 'SSE-KMS (alias/cg-infra)',
      Versioning: 'Enabled',
    },
  },
  {
    name: 'cg-static-site',
    region: 'us-east-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 219,
    metadata: {
      Objects: '1,902',
      Size: '740 MB',
      Encryption: 'SSE-S3 (AES-256)',
      'Served via': 'CloudFront (OAC)',
    },
  },
  {
    name: 'cg-backup-snapshots',
    region: 'eu-west-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 260,
    metadata: {
      Objects: '5,338',
      Size: '2.1 TB',
      Encryption: 'SSE-KMS (alias/cg-backup)',
      Replication: 'Cross-region from ap-south-1',
    },
  },
  {
    name: 'cg-ml-training-data',
    region: 'ap-southeast-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 132,
    metadata: {
      Objects: '77,204',
      Size: '890 GB',
      Encryption: 'SSE-KMS (alias/cg-ml)',
      Versioning: 'Enabled',
    },
  },
])

/* -------------------------------------------------------------------------- */
/* EC2 — 18 instances                                                         */
/* -------------------------------------------------------------------------- */

const EC2 = build('ec2', 'EC2 Instance', 'ec2', [
  {
    name: 'web-server-01',
    region: 'ap-south-1',
    status: 'high',
    openFindings: 3,
    ageDays: 96,
    metadata: {
      'Instance ID': 'i-0a4c81f39bd2e77a1',
      'Instance type': 't3.medium',
      'Public IPv4': '13.234.98.117',
      'Private IPv4': '10.0.2.41',
      'IMDS version': 'v1 and v2 (v1 permitted)',
      AMI: 'ami-0f5ee92e2d63afc18',
      'EBS encryption': 'Enabled (aws/ebs)',
      'IAM instance profile': 'web-server-role',
    },
    related: ['sg-web-public', 'production-db', 'cg-prod-assets'],
  },
  {
    name: 'legacy-app-01',
    region: 'ap-south-1',
    status: 'high',
    openFindings: 1,
    ageDays: 612,
    metadata: {
      'Instance ID': 'i-07be3f0c1a9d4e820',
      'Instance type': 'm5.large',
      'Public IPv4': '—',
      'Private IPv4': '10.0.5.18',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Disabled',
      AMI: 'ami-0b1c2d3e4f5a6b7c8 (Amazon Linux 2, EOL)',
    },
    tags: { Environment: 'production', Owner: 'legacy', ManagedBy: 'console' },
    related: ['sg-legacy-open'],
  },
  {
    name: 'batch-runner-01',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 148,
    metadata: {
      'Instance ID': 'i-0c93a7e5f1b8d2064',
      'Instance type': 'c5.xlarge',
      'Private IPv4': '10.0.6.72',
      'IMDS version': 'v2 only',
      AMI: 'ami-0e2f1a9c8b7d6e5f4 (312 days old)',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
  },
  {
    name: 'monitoring-01',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 240,
    metadata: {
      'Instance ID': 'i-04d8b1c6e9f3a7205',
      'Instance type': 't3.small',
      'Private IPv4': '10.0.7.11',
      'Detailed monitoring': 'Disabled',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
    related: ['sg-monitoring'],
  },
  {
    name: 'staging-mirror',
    region: 'ap-south-1',
    status: 'low',
    openFindings: 1,
    ageDays: 44,
    metadata: {
      'Instance ID': 'i-0b7f2e91c4a8d3e56',
      'Instance type': 't3.medium',
      'Private IPv4': '10.0.8.29',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
    tags: { Environment: 'production', ManagedBy: 'terraform' },
  },
  {
    name: 'gpu-trainer-01',
    region: 'ap-southeast-1',
    status: 'low',
    openFindings: 1,
    ageDays: 38,
    metadata: {
      'Instance ID': 'i-0f1e2d3c4b5a69780',
      'Instance type': 'g4dn.xlarge',
      'Private IPv4': '10.2.1.14',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-ml)',
    },
    tags: { Environment: 'production', Owner: 'ml-platform' },
  },
  {
    name: 'web-server-02',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 96,
    metadata: {
      'Instance ID': 'i-0d5a83c72e1f9b4a0',
      'Instance type': 't3.medium',
      'Private IPv4': '10.0.2.42',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
    related: ['sg-web-public', 'production-db'],
  },
  {
    name: 'web-server-03',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 71,
    metadata: {
      'Instance ID': 'i-01f9c4b7a3e8d2650',
      'Instance type': 't3.medium',
      'Private IPv4': '10.0.2.43',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
    related: ['sg-web-public'],
  },
  {
    name: 'api-gateway-01',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 188,
    metadata: {
      'Instance ID': 'i-092b4f8d1c6a3e750',
      'Instance type': 'c5.large',
      'Private IPv4': '10.0.3.17',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
    related: ['sg-api-internal', 'production-db'],
  },
  {
    name: 'api-gateway-02',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 188,
    metadata: {
      'Instance ID': 'i-0e73a1d9f2b5c8640',
      'Instance type': 'c5.large',
      'Private IPv4': '10.0.3.18',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
    related: ['sg-api-internal'],
  },
  {
    name: 'worker-queue-01',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 160,
    metadata: {
      'Instance ID': 'i-03c8e2a7b9d1f4520',
      'Instance type': 'm5.large',
      'Private IPv4': '10.0.4.21',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
  },
  {
    name: 'worker-queue-02',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 160,
    metadata: {
      'Instance ID': 'i-0a1b2c3d4e5f60718',
      'Instance type': 'm5.large',
      'Private IPv4': '10.0.4.22',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
  },
  {
    name: 'bastion-host',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 301,
    metadata: {
      'Instance ID': 'i-06f4d8b2c9a7e1350',
      'Instance type': 't3.micro',
      'Public IPv4': '13.201.44.9',
      'Private IPv4': '10.0.1.10',
      'IMDS version': 'v2 only',
      'Session Manager': 'Enabled',
    },
    related: ['sg-bastion-ssh'],
  },
  {
    name: 'jenkins-ci',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 274,
    metadata: {
      'Instance ID': 'i-0b9e7c5a3f1d84260',
      'Instance type': 'm5.xlarge',
      'Private IPv4': '10.0.9.31',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
  },
  {
    name: 'redis-cache-01',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 210,
    metadata: {
      'Instance ID': 'i-08d3f6a1b4c9e2570',
      'Instance type': 'r5.large',
      'Private IPv4': '10.0.5.44',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (aws/ebs)',
    },
    related: ['sg-cache-internal'],
  },
  {
    name: 'elasticsearch-01',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 196,
    metadata: {
      'Instance ID': 'i-05c1a9e7d3b6f2840',
      'Instance type': 'r5.xlarge',
      'Private IPv4': '10.0.5.45',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
    related: ['sg-cache-internal'],
  },
  {
    name: 'batch-runner-02',
    region: 'eu-west-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 148,
    metadata: {
      'Instance ID': 'i-0d2e4f6a8c1b39570',
      'Instance type': 'c5.xlarge',
      'Private IPv4': '10.1.6.73',
      'IMDS version': 'v2 only',
      'EBS encryption': 'Enabled (alias/cg-infra)',
    },
  },
  {
    name: 'vpn-endpoint',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 301,
    metadata: {
      'Instance ID': 'i-0917f3b5d8e2a4c60',
      'Instance type': 't3.small',
      'Public IPv4': '13.234.11.203',
      'Private IPv4': '10.0.1.11',
      'IMDS version': 'v2 only',
    },
  },
])

/* -------------------------------------------------------------------------- */
/* IAM — 9 identities                                                         */
/* -------------------------------------------------------------------------- */

const IAM = build('iam', 'IAM User', 'iam', [
  {
    name: 'developer-user',
    region: 'Global',
    status: 'high',
    openFindings: 1,
    ageDays: 210,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/developer-user',
      'Attached policies': 'AdministratorAccess',
      MFA: 'Enabled',
      'Access keys': '1 active',
      'Last activity': '2 hours ago',
      'Console access': 'Enabled',
    },
    tags: { Team: 'engineering', ManagedBy: 'console' },
  },
  {
    name: 'ci-deploy-bot',
    region: 'Global',
    status: 'high',
    openFindings: 1,
    ageDays: 402,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/ci-deploy-bot',
      'Attached policies': 'CloudGuardDeployPolicy',
      MFA: 'Not applicable (service account)',
      'Access keys': '1 active, created 214 days ago',
      'Last activity': '18 minutes ago',
      'Console access': 'Disabled',
    },
    tags: { Team: 'platform', Type: 'service-account' },
  },
  {
    name: 'test-user',
    region: 'Global',
    status: 'medium',
    openFindings: 1,
    ageDays: 88,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/test-user',
      'Attached policies': 'ReadOnlyAccess',
      MFA: 'Not enabled',
      'Access keys': 'None',
      'Last activity': '9 days ago',
      'Console access': 'Enabled',
    },
    tags: { Team: 'qa', ManagedBy: 'console' },
  },
  {
    name: 'contractor-temp',
    region: 'Global',
    status: 'medium',
    openFindings: 1,
    ageDays: 51,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/contractor-temp',
      'Attached policies': 'PowerUserAccess',
      MFA: 'Not enabled',
      'Access keys': 'None',
      'Last activity': '4 days ago',
      'Console access': 'Enabled',
    },
    tags: { Team: 'external', ManagedBy: 'console' },
  },
  {
    name: 'terraform-runner',
    region: 'Global',
    status: 'medium',
    openFindings: 1,
    ageDays: 301,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/terraform-runner',
      'Attached policies': 'CloudGuardInfraPolicy',
      'Inline policies': '1 (tf-state-write)',
      MFA: 'Not applicable (service account)',
      'Access keys': '1 active, created 62 days ago',
    },
    tags: { Team: 'platform', Type: 'service-account' },
  },
  {
    name: 'analytics-readonly',
    region: 'Global',
    status: 'low',
    openFindings: 1,
    ageDays: 176,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/analytics-readonly',
      'Attached policies': 'ReadOnlyAccess',
      MFA: 'Enabled',
      'Access keys': '1 active, unused 94 days',
      'Last activity': '94 days ago',
    },
    tags: { Team: 'analytics' },
  },
  {
    name: 'admin-ashutosh',
    region: 'Global',
    status: 'secure',
    openFindings: 0,
    ageDays: 402,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:user/admin-ashutosh',
      'Attached policies': 'AdministratorAccess',
      MFA: 'Enabled (hardware token)',
      'Access keys': 'None',
      'Last activity': '31 minutes ago',
    },
    tags: { Team: 'platform', Role: 'owner' },
  },
  {
    name: 'lambda-exec-role',
    region: 'Global',
    status: 'secure',
    openFindings: 0,
    ageDays: 288,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:role/lambda-exec-role',
      'Attached policies': 'AWSLambdaBasicExecutionRole',
      'Trust policy': 'lambda.amazonaws.com',
      'Max session duration': '1 hour',
    },
    tags: { Team: 'platform', Type: 'role' },
  },
  {
    name: 'ops-oncall',
    region: 'Global',
    status: 'secure',
    openFindings: 0,
    ageDays: 219,
    metadata: {
      ARN: 'arn:aws:iam::918273645500:role/ops-oncall',
      'Attached policies': 'CloudGuardIncidentResponse',
      'Trust policy': 'SSO (AWSReservedSSO_OpsOncall)',
      'Max session duration': '4 hours',
    },
    tags: { Team: 'sre', Type: 'role' },
  },
])

/* -------------------------------------------------------------------------- */
/* RDS — 2 databases                                                          */
/* -------------------------------------------------------------------------- */

const RDS = build('rds', 'RDS Instance', 'rds', [
  {
    name: 'production-db',
    region: 'ap-south-1',
    status: 'critical',
    openFindings: 1,
    ageDays: 288,
    metadata: {
      Identifier: 'production-db',
      Engine: 'PostgreSQL 15.5',
      'Instance class': 'db.r6g.xlarge',
      'Publicly accessible': 'Yes',
      Endpoint: 'production-db.cluster-c9xk2.ap-south-1.rds.amazonaws.com:5432',
      'Encryption at rest': 'Enabled (alias/cg-data)',
      'Backup retention': '7 days',
      'Multi-AZ': 'Enabled',
    },
    tags: { Environment: 'production', Owner: 'data-platform', Compliance: 'pci' },
    related: ['sg-db-private'],
  },
  {
    name: 'analytics-replica',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 176,
    metadata: {
      Identifier: 'analytics-replica',
      Engine: 'PostgreSQL 15.5',
      'Instance class': 'db.r6g.large',
      'Publicly accessible': 'No',
      'Encryption at rest': 'Enabled (alias/cg-data)',
      'Backup retention': '1 day',
      'Multi-AZ': 'Disabled',
    },
    tags: { Environment: 'production', Owner: 'analytics' },
    related: ['sg-db-private'],
  },
])

/* -------------------------------------------------------------------------- */
/* Security groups — 7                                                        */
/* -------------------------------------------------------------------------- */

const SG = build('security-group', 'Security Group', 'sg', [
  {
    name: 'sg-legacy-open',
    region: 'ap-south-1',
    status: 'critical',
    openFindings: 1,
    ageDays: 612,
    metadata: {
      'Group ID': 'sg-0f1a2b3c4d5e6f708',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': 'ALL traffic from 0.0.0.0/0',
      'Outbound rules': 'ALL traffic to 0.0.0.0/0',
      'Attached to': '1 instance (legacy-app-01)',
    },
    tags: { ManagedBy: 'console' },
    related: ['legacy-app-01'],
  },
  {
    name: 'sg-web-public',
    region: 'ap-south-1',
    status: 'high',
    openFindings: 1,
    ageDays: 301,
    metadata: {
      'Group ID': 'sg-04c8e2a19b7d35f60',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '80/tcp 0.0.0.0/0 · 443/tcp 0.0.0.0/0 · 22/tcp 0.0.0.0/0',
      'Attached to': '3 instances',
    },
    related: ['web-server-01', 'web-server-02', 'web-server-03'],
  },
  {
    name: 'sg-bastion-ssh',
    region: 'ap-south-1',
    status: 'high',
    openFindings: 1,
    ageDays: 301,
    metadata: {
      'Group ID': 'sg-02b7d4f8a1c9e3560',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '22/tcp 10.0.0.0/16 · 3389/tcp 0.0.0.0/0',
      'Attached to': '1 instance (bastion-host)',
    },
    related: ['bastion-host'],
  },
  {
    name: 'sg-api-internal',
    region: 'ap-south-1',
    status: 'medium',
    openFindings: 1,
    ageDays: 288,
    metadata: {
      'Group ID': 'sg-07e1c9a3b5d8f2460',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '8080/tcp 10.0.2.0/24',
      'Outbound rules': 'ALL traffic to 0.0.0.0/0',
      'Attached to': '2 instances',
    },
    related: ['api-gateway-01', 'api-gateway-02'],
  },
  {
    name: 'sg-monitoring',
    region: 'ap-south-1',
    status: 'low',
    openFindings: 1,
    ageDays: 240,
    metadata: {
      'Group ID': 'sg-09a4e8c2b6d1f3570',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '9090/tcp 10.0.7.0/24',
      'Attached to': '0 instances',
    },
  },
  {
    name: 'sg-db-private',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 288,
    metadata: {
      'Group ID': 'sg-03d9f1b7c4a8e2650',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '5432/tcp from sg-api-internal · 5432/tcp from sg-web-public',
      'Attached to': '2 databases',
    },
    related: ['production-db', 'analytics-replica'],
  },
  {
    name: 'sg-cache-internal',
    region: 'ap-south-1',
    status: 'secure',
    openFindings: 0,
    ageDays: 210,
    metadata: {
      'Group ID': 'sg-06b2d8f4a9c1e3750',
      VPC: 'vpc-0a1b2c3d (10.0.0.0/16)',
      'Inbound rules': '6379/tcp from sg-api-internal · 9200/tcp from sg-api-internal',
      'Attached to': '2 instances',
    },
    related: ['redis-cache-01', 'elasticsearch-01'],
  },
])

/* -------------------------------------------------------------------------- */

export const RESOURCES: CloudResource[] = [...S3, ...EC2, ...IAM, ...RDS, ...SG]

const BY_NAME = new Map(RESOURCES.map((r) => [r.name, r]))
const BY_ID = new Map(RESOURCES.map((r) => [r.id, r]))

/**
 * Rewrites the name-based `related` seeds into real ids, and mirrors every
 * relation so a link declared on one side shows up on both. Runs once at module
 * load; a name that matches nothing is a authoring bug, so it throws.
 */
function resolveRelations(): void {
  const mirrored = new Map<string, Set<string>>(RESOURCES.map((r) => [r.id, new Set<string>()]))

  for (const resource of RESOURCES) {
    for (const name of resource.relatedResourceIds) {
      const target = BY_NAME.get(name)
      if (!target) {
        throw new Error(`${resource.name} references unknown resource "${name}"`)
      }
      mirrored.get(resource.id)!.add(target.id)
      mirrored.get(target.id)!.add(resource.id)
    }
  }

  for (const resource of RESOURCES) {
    resource.relatedResourceIds = [...mirrored.get(resource.id)!]
  }
}

resolveRelations()

/** Inventory composition, fixed by the product spec. */
export const RESOURCE_COUNTS: { service: ServiceId; count: number }[] = [
  { service: 's3', count: S3.length },
  { service: 'ec2', count: EC2.length },
  { service: 'iam', count: IAM.length },
  { service: 'rds', count: RDS.length },
  { service: 'security-group', count: SG.length },
]

export const TOTAL_RESOURCES = RESOURCES.length

export function resourceById(id: string): CloudResource | undefined {
  return BY_ID.get(id)
}

export function resourceByName(name: string): CloudResource | undefined {
  return BY_NAME.get(name)
}

/**
 * Fails loudly in development if the inventory drifts from the spec, so a
 * mismatch surfaces here rather than as a wrong number on the dashboard.
 */
export function assertInventory(): void {
  if (TOTAL_RESOURCES !== 48) {
    throw new Error(`Inventory must hold 48 resources, found ${TOTAL_RESOURCES}`)
  }
  const expected: Record<string, number> = {
    s3: 12,
    ec2: 18,
    iam: 9,
    rds: 2,
    'security-group': 7,
  }
  for (const { service, count } of RESOURCE_COUNTS) {
    if (expected[service] !== count) {
      throw new Error(`Expected ${expected[service]} ${service} resources, found ${count}`)
    }
  }
}
