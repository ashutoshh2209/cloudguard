import React from 'react';
import { cn } from '../../utils/cn';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-9/50 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:opacity-50 disabled:pointer-events-none rounded-lg";
    
    const variants = {
      primary: "bg-gradient-to-b from-accent-10 to-accent-9 text-content-inverse hover:from-accent-11 hover:to-accent-9 border border-accent-10/50 shadow-sm hover-lift",
      secondary: "bg-surface-2 text-content hover:text-content-inverse border border-line hover:border-line-strong shadow-sm hover-lift",
      outline: "bg-transparent text-content-secondary hover:text-content border border-line hover:border-line-strong hover:bg-surface-2 hover-lift",
      ghost: "bg-transparent text-content-muted hover:text-content hover:bg-surface-2 border border-transparent",
    };
    
    const sizes = {
      sm: "px-3 py-1.5 text-xs",
      md: "px-4 py-2 text-sm",
      lg: "px-5 py-2.5 text-base",
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
