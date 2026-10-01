import React from 'react';
import { Search, Bell, Shield, ChevronDown, User, Activity, Menu } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { Button } from './ui/Button';

interface TopBarProps {
  onOpenCopilot?: () => void;
}

export function TopBar({ onOpenCopilot }: TopBarProps) {
  const location = useLocation();
  
  return (
    <header className="h-16 bg-canvas border-b border-line flex items-center justify-between px-4 md:px-8 sticky top-0 z-20">
      
      {/* Left side: Context & Search */}
      <div className="flex items-center gap-4 md:gap-6 flex-1">
        <button className="md:hidden p-2 -ml-2 text-content-muted hover:text-content hover:bg-surface-2 rounded-lg transition-colors">
          <Menu className="w-5 h-5" />
        </button>
        
        <div className="relative w-full max-w-sm hidden md:block">
          <Search className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input 
            type="text" 
            placeholder="Search resources, findings, or policies..." 
            className="w-full bg-surface-1 border border-line rounded py-1.5 pl-9 pr-4 text-[13px] text-content placeholder:text-content-muted focus:outline-none focus:border-accent-6 transition-colors shadow-sm"
          />
        </div>
        
        <div className="h-4 w-px bg-line hidden md:block" />
        
        <div className="hidden lg:flex items-center gap-2 text-[13px]">
          <span className="text-content-muted font-bold uppercase tracking-wider text-[11px]">Env:</span>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface-2 border border-line shadow-sm">
            <span className="w-2 h-2 rounded-full bg-severity-secure shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
            <span className="text-content font-medium">Production (us-east-1)</span>
          </div>
        </div>
      </div>

      {/* Right side: Actions & Profile */}
      <div className="flex items-center gap-3 md:gap-5">
        
        <Button variant="primary" className="hidden sm:flex">
          <Shield className="w-4 h-4 mr-2" />
          Run Security Scan
        </Button>
        <Button variant="primary" size="sm" className="sm:hidden px-2">
          <Shield className="w-4 h-4" />
        </Button>

        {onOpenCopilot && (
          <Button variant="outline" size="sm" onClick={onOpenCopilot} className="hidden sm:flex border-accent-9/30 hover:border-accent-9 text-accent-10 hover:text-accent-11 bg-accent-9/10 hover:bg-accent-9/20">
            Ask Copilot
          </Button>
        )}

        <div className="h-4 w-px bg-line hidden sm:block" />

        <button className="relative p-2 rounded-lg text-content-muted hover:text-content hover:bg-surface-2 border border-transparent hover:border-line transition-all shadow-sm">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-severity-critical border-2 border-canvas"></span>
        </button>

        <div className="h-4 w-px bg-line" />

        <button className="flex items-center gap-2 hover:bg-surface-2 p-1 md:pr-2 rounded-lg border border-transparent hover:border-line transition-all">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-accent-9 to-accent-11 flex items-center justify-center shadow-sm">
            <span className="text-[12px] font-bold text-white">AK</span>
          </div>
          <div className="hidden md:flex flex-col items-start ml-1">
            <span className="text-[13px] font-bold text-content leading-tight">Admin User</span>
            <span className="text-[11px] font-medium text-content-secondary leading-tight">SecOps Team</span>
          </div>
          <ChevronDown className="w-4 h-4 text-content-muted ml-1 hidden md:block" />
        </button>
      </div>

    </header>
  );
}
