import React from 'react';
import { cn } from '../../utils/cn';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'outline' | 'subtle';
  color?: 'blue' | 'gray' | 'red' | 'yellow' | 'green' | 'orange';
}

export function Badge({ 
  className, 
  variant = 'default', 
  color = 'gray',
  children, 
  ...props 
}: BadgeProps) {
  
  const baseStyles = "inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] uppercase tracking-wider font-semibold border";
  
  const colorStyles = {
    blue: {
      default: "bg-accent-9 text-content-inverse border-transparent",
      outline: "bg-transparent text-accent-10 border-accent-10",
      subtle: "bg-accent-subtle text-accent-10 border-transparent",
    },
    gray: {
      default: "bg-surface-3 text-content border-line",
      outline: "bg-transparent text-content-secondary border-line-strong",
      subtle: "bg-surface-2 text-content-secondary border-transparent",
    },
    red: {
      default: "bg-severity-critical text-content-inverse border-transparent",
      outline: "bg-transparent text-severity-critical-ink border-severity-critical",
      subtle: "bg-severity-critical/10 text-severity-critical-ink border-transparent",
    },
    orange: {
      default: "bg-severity-high text-content-inverse border-transparent",
      outline: "bg-transparent text-severity-high-ink border-severity-high",
      subtle: "bg-severity-high/10 text-severity-high-ink border-transparent",
    },
    yellow: {
      default: "bg-severity-medium text-content-inverse border-transparent",
      outline: "bg-transparent text-severity-medium-ink border-severity-medium",
      subtle: "bg-severity-medium/10 text-severity-medium-ink border-transparent",
    },
    green: {
      default: "bg-severity-secure text-content-inverse border-transparent",
      outline: "bg-transparent text-severity-secure-ink border-severity-secure",
      subtle: "bg-severity-secure/10 text-severity-secure-ink border-transparent",
    },
  };

  return (
    <span className={cn(baseStyles, colorStyles[color][variant], className)} {...props}>
      {children}
    </span>
  );
}
