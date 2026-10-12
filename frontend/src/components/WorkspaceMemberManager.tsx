import React, { useState, useEffect, useCallback } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { Users, UserPlus, Trash2, ShieldCheck, Mail, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { workspacesApi, WorkspaceMemberItem } from '../api/workspaces';

export function WorkspaceMemberManager() {
  const { activeWorkspace, user, refreshWorkspaces } = useAuth();
  const [members, setMembers] = useState<WorkspaceMemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [addEmail, setAddEmail] = useState('');
  const [addRole, setAddRole] = useState('MEMBER');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isOwner = activeWorkspace?.role === 'OWNER';
  const isAdmin = activeWorkspace?.role === 'ADMIN';
  const canManage = isOwner || isAdmin;

  const loadMembers = useCallback(async () => {
    if (!activeWorkspace) return;
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

  if (!activeWorkspace) {
    return (
      <Card>
        <p className="text-[14px] text-content-secondary">No workspace selected.</p>
      </Card>
    );
  }

  const getRoleBadgeColor = (role: string): 'blue' | 'gray' | 'red' | 'yellow' | 'green' | 'orange' => {
    switch (role) {
      case 'OWNER': return 'red';
      case 'ADMIN': return 'orange';
      case 'MEMBER': return 'blue';
      case 'VIEWER': return 'gray';
      default: return 'gray';
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Overview */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-content">{activeWorkspace.name}</h3>
            <p className="text-[13px] text-content-secondary mt-0.5">
              Your role: <span className="font-semibold text-accent-9">{activeWorkspace.role}</span>
            </p>
          </div>
          <Badge color={getRoleBadgeColor(activeWorkspace.role || 'MEMBER')}>
            {activeWorkspace.role}
          </Badge>
        </div>
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
