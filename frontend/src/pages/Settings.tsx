import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/Tabs';
import { Cloud, User, Bell, Shield, Users } from 'lucide-react';
import { AWSConnectionManager } from '../components/AWSConnectionManager';
import { WorkspaceMemberManager } from '../components/WorkspaceMemberManager';
import { useAuth } from '../context/AuthContext';

export function Settings() {
  const { user, isAuthenticated } = useAuth();

  return (
    <div className="max-w-5xl mx-auto flex flex-col animate-in fade-in duration-300">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-content">Settings</h1>
        <p className="text-[14px] text-content-secondary mt-1">Manage your account, workspaces, preferences, and cloud integrations.</p>
      </div>

      <Tabs defaultValue="account">
        <TabsList className="mb-8 self-start bg-surface-1 border border-line">
          <TabsTrigger value="account" className="flex items-center gap-2">
            <User className="w-4 h-4" /> Account
          </TabsTrigger>
          <TabsTrigger value="workspace" className="flex items-center gap-2">
            <Users className="w-4 h-4" /> Workspace & Members
          </TabsTrigger>
          <TabsTrigger value="cloud" className="flex items-center gap-2">
            <Cloud className="w-4 h-4" /> AWS Integration
          </TabsTrigger>
          <TabsTrigger value="scanning" className="flex items-center gap-2">
            <Shield className="w-4 h-4" /> Scan Preferences
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="w-4 h-4" /> Notifications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="account">
          <div className="space-y-6">
            {!isAuthenticated && (
              <Card className="border-accent-border bg-accent-subtle/40">
                <h3 className="text-lg font-bold text-content mb-2">Guest Preview Mode</h3>
                <p className="text-[14px] text-content-secondary mb-4">
                  You are currently exploring CloudGuard without signing in. Create an account or log in to save your profile, create custom workspaces, and connect your AWS environment.
                </p>
                <div className="flex items-center gap-3">
                  <Link to="/login">
                    <Button variant="outline">Log In</Button>
                  </Link>
                  <Link to="/register">
                    <Button variant="primary">Create Account</Button>
                  </Link>
                </div>
              </Card>
            )}
            <Card>
              <h3 className="text-lg font-bold text-content mb-4">Profile Information</h3>
              <div className="space-y-4 max-w-md">
                <div>
                  <label className="block text-[13px] font-bold text-content-secondary mb-1.5">Full Name</label>
                  <input type="text" key={user?.name} defaultValue={user?.name || "Guest User"} className="w-full bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50" />
                </div>
                <div>
                  <label className="block text-[13px] font-bold text-content-secondary mb-1.5">Email Address</label>
                  <input type="email" key={user?.email} defaultValue={user?.email || "guest@cloudguard.io"} className="w-full bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50" />
                </div>
                <Button variant="primary" className="mt-4">Save Changes</Button>
              </div>
            </Card>

            <Card className="border-severity-critical/20 bg-severity-critical/5">
              <h3 className="text-lg font-bold text-severity-critical-ink mb-2">Danger Zone</h3>
              <p className="text-[14px] text-content-secondary mb-4">Permanently delete your account and all associated data. This action cannot be undone.</p>
              <Button variant="outline" className="text-severity-critical-ink border-severity-critical hover:bg-severity-critical hover:text-content-inverse transition-colors">
                Delete Account
              </Button>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="workspace">
          <WorkspaceMemberManager />
        </TabsContent>

        <TabsContent value="cloud">
          <AWSConnectionManager />
        </TabsContent>

        <TabsContent value="scanning">
          <Card>
            <h3 className="text-lg font-bold text-content mb-4">Scan Schedule</h3>
            <p className="text-[14px] text-content-secondary mb-6">Configure when automated security assessments run.</p>
            
            <div className="space-y-4 max-w-md">
              <div>
                <label className="block text-[13px] font-bold text-content-secondary mb-1.5">Frequency</label>
                <select className="w-full bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50">
                  <option>Daily</option>
                  <option>Weekly</option>
                  <option>Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-bold text-content-secondary mb-1.5">Time (UTC)</label>
                <input type="time" defaultValue="02:00" className="w-full bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50" />
              </div>
              <Button variant="primary" className="mt-4">Save Schedule</Button>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <h3 className="text-lg font-bold text-content mb-4">Alert Preferences</h3>
            <div className="space-y-4">
              <label className="flex items-center gap-3">
                <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-line bg-surface-1 text-accent-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9/50" />
                <span className="text-[14px] text-content">Email alerts for Critical findings</span>
              </label>
              <label className="flex items-center gap-3">
                <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-line bg-surface-1 text-accent-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9/50" />
                <span className="text-[14px] text-content">Email alerts for High findings</span>
              </label>
              <label className="flex items-center gap-3">
                <input type="checkbox" className="w-4 h-4 rounded border-line bg-surface-1 text-accent-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9/50" />
                <span className="text-[14px] text-content">Weekly summary reports</span>
              </label>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
