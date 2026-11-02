import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, ChevronRight, Server, Database, Cloud } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useAuth } from '../context/AuthContext';

export function Landing() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-canvas text-content flex flex-col font-sans selection:bg-accent-subtle">
      <header className="h-20 border-b border-line flex items-center justify-between px-8 md:px-16 z-20 bg-surface-1/80 backdrop-blur-md sticky top-0">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-accent-9 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
          <span className="text-content font-bold text-xl tracking-tight">CloudGuard</span>
        </div>
        <div className="flex items-center gap-4 md:gap-6 text-sm font-medium">
          <a href="#features" className="hidden sm:inline text-content-secondary hover:text-content transition-colors">Features</a>
          <a href="#how-it-works" className="hidden sm:inline text-content-secondary hover:text-content transition-colors">How it Works</a>
          {!isAuthenticated && (
            <>
              <Link to="/login" className="text-content-secondary hover:text-content transition-colors">
                Log In
              </Link>
              <Link to="/register">
                <Button variant="outline" size="sm" className="hidden sm:inline-flex">
                  Create Account
                </Button>
              </Link>
            </>
          )}
          <Link to="/app">
            <Button variant="primary">
              Launch Console
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative pt-32 pb-40 overflow-hidden flex flex-col items-center justify-center text-center px-4">
          <div className="absolute inset-0 blueprint blueprint-fade opacity-30 pointer-events-none" />
          
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent-border bg-accent-subtle text-accent-10 text-xs font-bold uppercase tracking-wider mb-8 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-accent-9 animate-pulse" />
            Enterprise Security Posture Management
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tighter text-content mb-6 max-w-4xl animate-rise-in" style={{ animationDelay: '100ms' }}>
            Know what's exposed. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-9 to-accent-11">Secure what's critical.</span>
          </h1>
          
          <p className="text-lg md:text-xl text-content-secondary max-w-2xl mb-10 animate-rise-in" style={{ animationDelay: '200ms' }}>
            Continuous monitoring, instant threat detection, and automated remediation for your entire AWS infrastructure. Built for enterprise scale.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-4 animate-rise-in" style={{ animationDelay: '300ms' }}>
            <Link to="/app">
              <Button variant="primary" className="h-12 px-8 text-base">
                View Dashboard
                <ChevronRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            {!isAuthenticated ? (
              <Link to="/register">
                <Button variant="outline" className="h-12 px-8 text-base bg-surface-1">
                  Create Free Account
                </Button>
              </Link>
            ) : (
              <Link to="/app/settings">
                <Button variant="outline" className="h-12 px-8 text-base bg-surface-1">
                  Workspace Settings
                </Button>
              </Link>
            )}
          </div>
        </section>

        <div className="rule-fade w-full max-w-5xl mx-auto" />

        {/* Features Preview */}
        <section id="features" className="py-32 px-8 md:px-16 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="panel p-8 hover-lift">
              <div className="w-12 h-12 rounded-lg bg-accent-subtle border border-accent-border flex items-center justify-center mb-6">
                <Cloud className="w-6 h-6 text-accent-9" />
              </div>
              <h3 className="text-xl font-bold text-content mb-3">Multi-Account Visibility</h3>
              <p className="text-content-secondary leading-relaxed">
                Connect and monitor all your AWS accounts from a single pane of glass. Discover shadow IT and orphaned resources instantly.
              </p>
            </div>
            
            <div className="panel p-8 hover-lift">
              <div className="w-12 h-12 rounded-lg bg-surface-2 border border-line flex items-center justify-center mb-6">
                <Database className="w-6 h-6 text-severity-critical" />
              </div>
              <h3 className="text-xl font-bold text-content mb-3">Real-time Risk Detection</h3>
              <p className="text-content-secondary leading-relaxed">
                Identify misconfigurations, exposed databases, and overly permissive IAM roles as soon as they are deployed.
              </p>
            </div>

            <div className="panel p-8 hover-lift">
              <div className="w-12 h-12 rounded-lg bg-surface-2 border border-line flex items-center justify-center mb-6">
                <Server className="w-6 h-6 text-severity-secure" />
              </div>
              <h3 className="text-xl font-bold text-content mb-3">Compliance Automation</h3>
              <p className="text-content-secondary leading-relaxed">
                Continuously map your infrastructure against CIS, SOC2, and PCI-DSS frameworks with automated reporting.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-12 text-center text-content-muted text-sm bg-surface-1">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Shield className="w-5 h-5 text-accent-9 opacity-50" />
          <span className="font-bold tracking-tight">CloudGuard</span>
        </div>
        <p>© 2026 CloudGuard Security. All rights reserved.</p>
      </footer>
    </div>
  );
}
