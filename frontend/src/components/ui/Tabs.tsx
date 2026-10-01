import React from 'react';
import { cn } from '../../utils/cn';

interface TabsProps {
  defaultValue: string;
  className?: string;
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function Tabs({ defaultValue, className, children, value, onValueChange }: TabsProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);
  
  const selectedValue = value !== undefined ? value : internalValue;
  
  const handleValueChange = (newValue: string) => {
    if (value === undefined) {
      setInternalValue(newValue);
    }
    onValueChange?.(newValue);
  };

  return (
    <div className={cn("flex flex-col w-full", className)} data-state={selectedValue}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            selectedValue,
            onValueChange: handleValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

interface TabsListProps {
  className?: string;
  children: React.ReactNode;
  selectedValue?: string;
  onValueChange?: (value: string) => void;
}

export function TabsList({ className, children, selectedValue, onValueChange }: TabsListProps) {
  return (
    <div className={cn("inline-flex h-9 items-center justify-center rounded-lg bg-surface-3 p-1 text-content-muted", className)}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            selectedValue,
            onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

interface TabsTriggerProps {
  value: string;
  className?: string;
  children: React.ReactNode;
  selectedValue?: string;
  onValueChange?: (value: string) => void;
}

export function TabsTrigger({ value, className, children, selectedValue, onValueChange }: TabsTriggerProps) {
  const isSelected = selectedValue === value;
  
  return (
    <button
      type="button"
      onClick={() => onValueChange?.(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        isSelected ? "bg-surface-1 text-content shadow-sm" : "hover:text-content hover:bg-surface-2",
        className
      )}
      data-state={isSelected ? 'active' : 'inactive'}
    >
      {children}
    </button>
  );
}

interface TabsContentProps {
  value: string;
  className?: string;
  children: React.ReactNode;
  selectedValue?: string;
}

export function TabsContent({ value, className, children, selectedValue }: TabsContentProps) {
  const isSelected = selectedValue === value;
  
  if (!isSelected) return null;
  
  return (
    <div className={cn("mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9 focus-visible:ring-offset-2", className)} data-state={isSelected ? 'active' : 'inactive'}>
      {children}
    </div>
  );
}
