import type { CloudAccount } from '@/types'
import { daysAgo } from './_time'

/**
 * Connected cloud accounts.
 *
 * Nothing here authenticates against AWS — these are inert records describing
 * how a real deployment *would* be wired (a read-only AssumeRole audit role).
 * The frontend never holds credentials.
 */

export const ACCOUNTS: CloudAccount[] = [
  {
    id: 'acct-prod',
    name: 'Production Environment',
    accountId: '918273645500',
    alias: 'cloudguard-prod',
    provider: 'aws',
    environment: 'production',
    defaultRegion: 'ap-south-1',
    enabledRegions: ['ap-south-1', 'us-east-1', 'eu-west-1', 'ap-southeast-1'],
    status: 'connected',
    accessMethod: 'IAM role · AssumeRole (read-only)',
    roleArn: 'arn:aws:iam::918273645500:role/CloudGuardSecurityAudit',
    connectedAt: daysAgo(34),
    resourceCount: 48,
    securityScore: 72,
  },
  {
    id: 'acct-staging',
    name: 'Staging',
    accountId: '402918375611',
    alias: 'cloudguard-staging',
    provider: 'aws',
    environment: 'staging',
    defaultRegion: 'ap-south-1',
    enabledRegions: ['ap-south-1', 'eu-west-1'],
    status: 'connected',
    accessMethod: 'IAM role · AssumeRole (read-only)',
    roleArn: 'arn:aws:iam::402918375611:role/CloudGuardSecurityAudit',
    connectedAt: daysAgo(21),
    resourceCount: 23,
    securityScore: 81,
  },
  {
    id: 'acct-sandbox',
    name: 'Developer Sandbox',
    accountId: '551204983377',
    alias: 'cloudguard-sandbox',
    provider: 'aws',
    environment: 'development',
    defaultRegion: 'us-east-1',
    enabledRegions: ['us-east-1'],
    status: 'disconnected',
    accessMethod: 'IAM role · AssumeRole (read-only)',
    roleArn: 'arn:aws:iam::551204983377:role/CloudGuardSecurityAudit',
    connectedAt: daysAgo(96),
    resourceCount: 0,
    securityScore: 0,
  },
]

/** The account every page is scoped to. Account switching is UI-only for now. */
export const ACTIVE_ACCOUNT = ACCOUNTS[0]
