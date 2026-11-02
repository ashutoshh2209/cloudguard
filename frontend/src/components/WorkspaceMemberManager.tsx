import React, { useState, useEffect, useCallback } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { Users, UserPlus, Trash2, Mail, Loader2, Briefcase, Plus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { workspacesApi, WorkspaceMemberItem } from '../api/workspaces';

export function WorkspaceMemberManager() {
  const { workspaces, activeWorkspace, switchWorkspace, createWorkspace, user, refreshWorkspaces } = useAuth();
  const [members, setMembers] = useState<WorkspaceMemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [addEmail, setAddEmail] = useState('');
  const [addRole, setAddRole] = useState('MEMBER');
  const [adding, setAdding] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isOwner = activeWorkspace?.role === 'OWNER';
  const isAdmin = activeWorkspace?.role === 'ADMIN';
  const canManage = isOwner || isAdmin;

  const loadMembers = useCallback(async () => {
    if (!activeWorkspace) {
      setMembers([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError('');
      const data = await workspacesApi.listMembers(activeWorkspace.id);
      setMembers(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load members');
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim() || creatingWorkspace) return;
    try {
      setCreatingWorkspace(true);
      setError('');
      setSuccess('');
      const created = await createWorkspace(newWorkspaceName.trim());
      setNewWorkspaceName('');
      setShowCreateForm(false);
      setSuccess(`Created and selected workspace "${created.name}"`);
    } catch (err: any) {
      setError(err.message || 'Failed to create workspace');
    } finally {
      setCreatingWorkspace(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !addEmail.trim()) return;
    try {
      setAdding(true);
      setError('');
      setSuccess('');
      await workspacesApi.addMember(activeWorkspace.id, addEmail.trim(), addRole);
      setAddEmail('');
      setSuccess(`Added member successfully`);
      await loadMembers();
      await refreshWorkspaces();
    } catch (err: any) {
      setError(err.message || 'Failed to add member');
    } finally {
      setAdding(false);
    }
  };

  const handleRoleChange = async (memberUserId: string, newRole: string) => {
    if (!activeWorkspace) return;
    try {
      setError('');
      await workspacesApi.updateMemberRole(activeWorkspace.id, memberUserId, newRole);
      await loadMembers();
    } catch (err: any) {
      setError(err.message || 'Failed to update member role');
    }
  };

  const handleRemoveMember = async (memberUserId: string) => {
    if (!activeWorkspace) return;
    try {
      setError('');
      await workspacesApi.removeMember(activeWorkspace.id, memberUserId);
      await loadMembers();
      await refreshWorkspaces();
    } catch (err: any) {
      setError(err.message || 'Failed to remove member');
    }
  };

  const getRoleBadgeColor = (role: string): 'blue' | 'gray' | 'red' | 'yellow' | 'green' | 'orange' => {
    switch (role) {
      case 'OWNER': return 'red';
      case 'ADMIN': return 'orange';
      case 'MEMBER': return 'blue';
      case 'VIEWER': return 'gray';
      default: return 'gray';
    }
  };

  if (!activeWorkspace) {
    return (
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-accent-9" />
          <h3 className="text-lg font-bold text-content">Select or Create a Workspace</h3>
        </div>
        <p className="text-[14px] text-content-secondary">
          No active workspace is currently selected. Select an existing workspace below or create a new one.
        </p>

        {workspaces.length > 0 && (
          <div className="space-y-2">
            <label className="block text-[12px] font-bold uppercase tracking-wider text-content-muted">
              Available Workspaces
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => switchWorkspace(ws.id)}
                  className="flex items-center justify-between p-3 rounded-lg border border-line bg-surface-1 hover:border-accent-9 text-left transition-colors"
                >
                  <div>
                    <div className="text-[14px] font-semibold text-content">{ws.name}</div>
                    <div className="text-[11px] text-content-muted font-mono">{ws.id}</div>
                  </div>
                  <Badge color={getRoleBadgeColor(ws.role || 'OWNER')}>{ws.role || 'OWNER'}</Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleCreateWorkspace} className="flex flex-col sm:flex-row gap-3 pt-2">
          <input
            type="text"
            required
            placeholder="New workspace name (e.g., Production AWS)"
            value={newWorkspaceName}
            onChange={(e) => setNewWorkspaceName(e.target.value)}
            className="flex-1 bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
          />
          <Button variant="primary" type="submit" disabled={creatingWorkspace || !newWorkspaceName.trim()}>
            {creatingWorkspace ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Workspace'}
          </Button>
        </form>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Overview & Switcher */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-lg font-bold text-content">{activeWorkspace.name}</h3>
              <Badge color={getRoleBadgeColor(activeWorkspace.role || 'OWNER')}>
                {activeWorkspace.role || 'OWNER'}
              </Badge>
            </div>
            <p className="text-[12px] text-content-muted font-mono mt-1">
              Workspace ID: {activeWorkspace.id}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {workspaces.length > 1 && (
              <select
                aria-label="Active workspace"
                value={activeWorkspace.id}
                onChange={(e) => switchWorkspace(e.target.value)}
                className="bg-surface-2 border border-line rounded-lg px-3 py-1.5 text-[13px] text-content focus:outline-none focus:border-accent-9/50"
              >
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name} ({ws.role || 'OWNER'})
                  </option>
                ))}
              </select>
            )}
            <Button
              variant="outline"
              size="sm"
              type="button"
              onClick={() => setShowCreateForm((prev) => !prev)}
              className="flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              New Workspace
            </Button>
          </div>
        </div>

        {showCreateForm && (
          <form onSubmit={handleCreateWorkspace} className="mt-4 pt-4 border-t border-line flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              required
              placeholder="New workspace name (e.g., Production AWS)"
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              className="flex-1 bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
            />
            <Button variant="primary" type="submit" disabled={creatingWorkspace || !newWorkspaceName.trim()}>
              {creatingWorkspace ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create & Select'}
            </Button>
          </form>
        )}
      </Card>

      {/* Add Member Form (Admins / Owners only) */}
      {canManage && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="w-4 h-4 text-accent-9" />
            <h3 className="text-md font-bold text-content">Add Workspace Member</h3>
          </div>

          {error && (
            <div className="mb-4 bg-severity-critical/10 border border-severity-critical/30 rounded-md p-3 text-sm text-severity-critical-ink">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 bg-severity-secure/10 border border-severity-secure/30 rounded-md p-3 text-sm text-severity-secure-ink">
              {success}
            </div>
          )}

          <form onSubmit={handleAddMember} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Mail className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                placeholder="colleague@example.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
                className="w-full bg-surface-1 border border-line rounded-lg pl-9 pr-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
              />
            </div>
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value)}
              className="bg-surface-1 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
            >
              <option value="MEMBER">Member</option>
              <option value="VIEWER">Viewer</option>
              {isOwner && <option value="ADMIN">Admin</option>}
            </select>
            <Button variant="primary" type="submit" disabled={adding}>
              {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Invite'}
            </Button>
          </form>
        </Card>
      )}

      {/* Members List */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-4 h-4 text-accent-9" />
          <h3 className="text-md font-bold text-content">Members ({members.length})</h3>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-accent-9" />
          </div>
        ) : (
          <div className="divide-y divide-line">
            {members.map((m) => {
              const isSelf = user?.id === m.user_id;
              const isMemberOwner = m.role === 'OWNER';

              return (
                <div key={m.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-surface-2 border border-line flex items-center justify-center font-bold text-[12px] text-content">
                      {m.full_name ? m.full_name.charAt(0).toUpperCase() : 'U'}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold text-content">{m.full_name}</span>
                        {isSelf && (
                          <span className="text-[10px] px-1 rounded bg-accent-9/10 text-accent-10 font-medium">You</span>
                        )}
                      </div>
                      <span className="text-[12px] text-content-secondary">{m.email}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {canManage && !isMemberOwner && !isSelf ? (
                      <select
                        value={m.role}
                        onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                        className="bg-surface-2 border border-line rounded px-2 py-1 text-[12px] text-content focus:outline-none"
                      >
                        <option value="VIEWER">VIEWER</option>
                        <option value="MEMBER">MEMBER</option>
                        {isOwner && <option value="ADMIN">ADMIN</option>}
                      </select>
                    ) : (
                      <Badge color={getRoleBadgeColor(m.role)}>{m.role}</Badge>
                    )}

                    {canManage && !isMemberOwner && !isSelf && (
                      <button
                        onClick={() => handleRemoveMember(m.user_id)}
                        className="p-1 text-content-muted hover:text-severity-critical-ink hover:bg-surface-2 rounded transition-colors"
                        title="Remove member"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}

                    {isSelf && !isMemberOwner && (
                      <button
                        onClick={() => handleRemoveMember(m.user_id)}
                        className="text-[12px] text-severity-critical-ink hover:underline"
                      >
                        Leave
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
