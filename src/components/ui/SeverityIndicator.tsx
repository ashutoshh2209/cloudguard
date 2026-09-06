import React from 'react';
import { cn } from '../../utils/cn';
import { Severity } from '../../types';

interface SeverityIndicatorProps {
  severity: Severity;
  className?: string;
  showLabel?: boolean;
}

export function SeverityIndicator({ severity, className, showLabel = true }: SeverityIndicatorProps) {
  // Using explicit colors that map to the design guidelines
  const colorMap: Record<Severity, string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-blue-400',
    secure: 'bg-green-500'
  };

  const textColorMap: Record<Severity, string> = {
    critical: 'text-red-400',
    high: 'text-orange-400',
    medium: 'text-yellow-400',
    low: 'text-blue-400',
    secure: 'text-green-400'
  };

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <span className="relative flex h-2 w-2">
        <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-75", colorMap[severity], severity === 'critical' || severity === 'high' ? 'animate-ping' : '')}></span>
        <span className={cn("relative inline-flex rounded-full h-2 w-2", colorMap[severity])}></span>
      </span>
      {showLabel && (
        <span className={cn("text-xs font-medium uppercase tracking-wider", textColorMap[severity])}>
          {severity}
        </span>
      )}
    </div>
  );
}
