import React from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  AlertCircle, 
  Server, 
  History, 
  FileText, 
  CheckCircle,
  Cloud,
  Sliders,
  Puzzle,
  Settings,
  HelpCircle,
  ChevronDown
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '../utils/cn';

const MAIN_NAV = [
  { name: 'Overview', to: '/app', icon: LayoutDashboard, exact: true },
  { name: 'Findings', to: '/app/findings', icon: AlertCircle },
  { name: 'Resources', to: '/app/resources', icon: Server },
  { name: 'Infrastructure', to: '/app/infrastructure', icon: Puzzle },
  { name: 'Scan History', to: '/app/scans', icon: History },
  { name: 'Reports', to: '/app/reports', icon: FileText },
];

export function Sidebar() {
  return (
    <aside className="w-[260px] h-screen bg-surface-1 border-r border-line hidden md:flex flex-col flex-shrink-0 relative z-20">
      
      {/* Brand */}
      <div className="h-16 px-6 flex flex-col justify-center border-b border-line shadow-sm bg-surface-1">
        <NavLink to="/" className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-accent-9 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
          <div className="flex flex-col">
            <span className="text-content font-bold text-[15px] tracking-tight leading-tight">CloudGuard</span>
            <span className="text-accent-9 text-[11px] font-medium tracking-wide">AWS Security Platform</span>
          </div>
        </NavLink>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 no-scrollbar bg-canvas">
        
        {/* Main Navigation */}
        <nav className="space-y-1">
          {MAIN_NAV.map((item) => (
            <NavLink
              key={item.name}
              to={item.to}
              end={item.exact}
              className={({ isActive }) => cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-200 group",
                isActive 
                  ? "bg-surface-2 text-content shadow-sm border border-line" 
                  : "text-content-muted hover:text-content hover:bg-surface-2 border border-transparent hover-lift"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={cn(
                    "w-4 h-4 transition-colors", 
                    isActive ? "text-accent-9" : "text-content-muted group-hover:text-content-secondary"
                  )} />
                  {item.name}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Bottom Section */}
      <div className="p-4 border-t border-line space-y-1 bg-surface-1">
        <NavLink to="/app/settings" className={({ isActive }) => cn(
          "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors border",
          isActive ? "bg-surface-2 text-content border-line" : "text-content-muted hover:text-content hover:bg-surface-2 border-transparent"
        )}>
          <Settings className="w-4 h-4" />
          Settings
        </NavLink>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium text-content-muted hover:text-content hover:bg-surface-2 transition-colors border border-transparent">
          <HelpCircle className="w-4 h-4 text-content-muted" />
          Help & Docs
        </button>
        
        <div className="mt-4 pt-4 border-t border-line">
          <button className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-surface-2 border border-line shadow-sm hover:border-accent-border transition-all text-left group">
            <div className="flex flex-col">
              <span className="text-[11px] text-content-muted font-bold mb-0.5 uppercase tracking-wider">Environment</span>
              <span className="text-[13px] text-content font-semibold group-hover:text-accent-9 transition-colors">Production</span>
            </div>
            <ChevronDown className="w-4 h-4 text-content-muted group-hover:text-content-secondary transition-colors" />
          </button>
        </div>
      </div>
      
    </aside>
  );
}
