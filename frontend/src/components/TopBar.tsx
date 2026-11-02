import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, Shield, ChevronDown, User, Activity, Menu, LogOut } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from './ui/Button';
import { useAuth } from '../context/AuthContext';

interface TopBarProps {
  onOpenCopilot?: () => void;
}

export function TopBar({ onOpenCopilot }: TopBarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, activeWorkspace, workspaces, isAuthenticated, switchWorkspace, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [wsOpen, setWsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const wsMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
      if (wsMenuRef.current && !wsMenuRef.current.contains(event.target as Node)) {
        setWsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    setProfileOpen(false);
    await logout();
    navigate('/login');
  };

  const getInitials = (name?: string) => {
    if (!name) return 'CG';
    const parts = name.trim().split(' ');
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

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
        
        <div className="hidden lg:flex items-center gap-2 text-[13px] relative" ref={wsMenuRef}>
          <span className="text-content-muted font-bold uppercase tracking-wider text-[11px]">Workspace:</span>
          <button
            type="button"
            onClick={() => setWsOpen(!wsOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-2 border border-line hover:border-accent-border shadow-sm transition-colors"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                activeWorkspace
                  ? 'bg-severity-secure shadow-[0_0_6px_rgba(16,185,129,0.4)]'
                  : 'bg-content-muted'
              }`}
            />
            <span className="text-content font-medium">
              {activeWorkspace ? activeWorkspace.name : 'No Workspace Selected'}
            </span>
            {activeWorkspace?.role && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-surface-1 border border-line text-content-secondary">
                {activeWorkspace.role}
              </span>
            )}
            <ChevronDown className="w-3.5 h-3.5 text-content-muted" />
          </button>

          {wsOpen && workspaces.length > 0 && (
            <div className="absolute left-0 top-full mt-2 w-64 rounded-lg bg-surface-1 border border-line shadow-xl py-1.5 z-50">
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-content-muted border-b border-line">
                Switch Workspace
              </div>
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  type="button"
                  onClick={() => {
                    switchWorkspace(ws.id);
                    setWsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-left text-[13px] hover:bg-surface-2 transition-colors ${
                    activeWorkspace?.id === ws.id ? 'text-accent-9 font-semibold bg-surface-2/60' : 'text-content'
                  }`}
                >
                  <span className="truncate pr-2">{ws.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 border border-line text-content-secondary">
                    {ws.role}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right side: Actions & Profile */}
      <div className="flex items-center gap-3 md:gap-4">
        
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

        {!isAuthenticated ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate('/login')}>
              Log In
            </Button>
            <Button variant="primary" size="sm" onClick={() => navigate('/register')}>
              Sign Up
            </Button>
          </div>
        ) : (
          <div className="relative" ref={menuRef}>
            <button 
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 hover:bg-surface-2 p-1 md:pr-2 rounded-lg border border-transparent hover:border-line transition-all focus:outline-none"
            >
              <div className="w-8 h-8 rounded bg-gradient-to-tr from-accent-9 to-accent-11 flex items-center justify-center shadow-sm">
                <span className="text-[12px] font-bold text-white">{getInitials(user?.name)}</span>
              </div>
              <div className="hidden md:flex flex-col items-start ml-1">
                <span className="text-[13px] font-bold text-content leading-tight">{user?.name || 'Admin User'}</span>
                <span className="text-[11px] font-medium text-content-secondary leading-tight">{user?.email || 'SecOps Team'}</span>
              </div>
              <ChevronDown className="w-4 h-4 text-content-muted ml-1 hidden md:block" />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-lg bg-surface-1 border border-line shadow-lg py-1.5 z-50">
                <div className="px-4 py-2 border-b border-line">
                  <p className="text-[13px] font-semibold text-content truncate">{user?.name || 'User'}</p>
                  <p className="text-[11px] text-content-secondary truncate">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2 text-[13px] text-severity-critical-ink hover:bg-surface-2 transition-colors text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Log out</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

    </header>
  );
}
