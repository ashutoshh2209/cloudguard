import React, { useState, useRef, useEffect } from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  AlertCircle, 
  Server, 
  History, 
  FileText, 
  Puzzle, 
  Settings, 
  HelpCircle, 
  ChevronDown,
  Check,
  Plus
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '../utils/cn';
import { useAuth } from '../context/AuthContext';

const MAIN_NAV = [
  { name: 'Overview', to: '/app', icon: LayoutDashboard, exact: true },
  { name: 'Findings', to: '/app/findings', icon: AlertCircle },
  { name: 'Resources', to: '/app/resources', icon: Server },
  { name: 'Infrastructure', to: '/app/infrastructure', icon: Puzzle },
  { name: 'Scan History', to: '/app/scans', icon: History },
  { name: 'Reports', to: '/app/reports', icon: FileText },
];

export function Sidebar() {
  const { activeWorkspace, workspaces, isAuthenticated, switchWorkspace, createWorkspace } = useAuth();
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setWorkspaceOpen(false);
        setIsCreating(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    try {
      await createWorkspace(newWorkspaceName.trim());
      setNewWorkspaceName('');
      setIsCreating(false);
      setWorkspaceOpen(false);
    } catch (err) {
      console.error('Failed to create workspace', err);
    }
  };

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
        
        {/* Workspace Selector */}
        <div className="mt-4 pt-4 border-t border-line relative" ref={menuRef}>
          <button 
            onClick={() => setWorkspaceOpen(!workspaceOpen)}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-surface-2 border border-line shadow-sm hover:border-accent-border transition-all text-left group"
          >
            <div className="flex flex-col min-w-0 pr-2">
              <span className="text-[11px] text-content-muted font-bold mb-0.5 uppercase tracking-wider">
                Workspace
              </span>
              <span className="text-[13px] text-content font-semibold group-hover:text-accent-9 transition-colors truncate">
                {activeWorkspace ? activeWorkspace.name : 'No Workspace Selected'}
              </span>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {activeWorkspace?.role && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-surface-1 border border-line text-content-secondary">
                  {activeWorkspace.role}
                </span>
              )}
              <ChevronDown className="w-4 h-4 text-content-muted group-hover:text-content-secondary transition-colors" />
            </div>
          </button>

          {workspaceOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-full rounded-lg bg-surface-1 border border-line shadow-xl py-2 z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
              <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-content-muted border-b border-line">
                {isAuthenticated ? 'Your Workspaces' : 'Preview Workspace'}
              </div>
              {!isAuthenticated ? (
                <div className="p-3 space-y-2">
                  <p className="text-[12px] text-content-secondary">
                    Sign in or create an account to manage custom workspaces and connect live AWS environments.
                  </p>
                  <div className="flex gap-2 pt-1">
                    <NavLink
                      to="/login"
                      onClick={() => setWorkspaceOpen(false)}
                      className="flex-1 text-center py-1.5 px-2 rounded bg-surface-2 border border-line text-[12px] font-semibold text-content hover:border-accent-9 transition-colors"
                    >
                      Log In
                    </NavLink>
                    <NavLink
                      to="/register"
                      onClick={() => setWorkspaceOpen(false)}
                      className="flex-1 text-center py-1.5 px-2 rounded bg-accent-9 text-white text-[12px] font-semibold hover:bg-accent-10 transition-colors"
                    >
                      Sign Up
                    </NavLink>
                  </div>
                </div>
              ) : (
                <>
                  <div className="max-h-48 overflow-y-auto py-1">
                    {workspaces.map((ws) => (
                      <button
                        key={ws.id}
                        onClick={() => {
                          switchWorkspace(ws.id);
                          setWorkspaceOpen(false);
                        }}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 text-left text-[13px] hover:bg-surface-2 transition-colors",
                          activeWorkspace?.id === ws.id ? "text-accent-9 font-semibold bg-surface-2/60" : "text-content font-medium"
                        )}
                      >
                        <span className="truncate pr-2">{ws.name}</span>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-2 border border-line text-content-secondary">
                            {ws.role}
                          </span>
                          {activeWorkspace?.id === ws.id && <Check className="w-3.5 h-3.5 text-accent-9" />}
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className="border-t border-line mt-1 pt-1 px-2">
                    {!isCreating ? (
                      <button
                        onClick={() => setIsCreating(true)}
                        className="w-full flex items-center gap-2 px-2 py-1.5 text-[12px] font-medium text-accent-9 hover:bg-surface-2 rounded transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Create Workspace</span>
                      </button>
                    ) : (
                      <form onSubmit={handleCreateWorkspace} className="space-y-1.5 py-1">
                        <input
                          type="text"
                          autoFocus
                          required
                          placeholder="Workspace name"
                          value={newWorkspaceName}
                          onChange={(e) => setNewWorkspaceName(e.target.value)}
                          className="w-full bg-surface-2 border border-line rounded px-2 py-1 text-[12px] text-content focus:outline-none focus:border-accent-9"
                        />
                        <div className="flex gap-1 justify-end">
                          <button
                            type="button"
                            onClick={() => setIsCreating(false)}
                            className="px-2 py-0.5 text-[11px] rounded text-content-secondary hover:bg-surface-2"
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            className="px-2 py-0.5 text-[11px] rounded bg-accent-9 text-white font-medium hover:bg-accent-10"
                          >
                            Save
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
      
    </aside>
  );
}
