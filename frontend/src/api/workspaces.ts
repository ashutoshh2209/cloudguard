import { fetchApi } from './client';

export interface WorkspaceItem {
  id: string;
  name: string;
  owner_id: string;
  current_user_role?: string;
  member_count?: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMemberItem {
  id: string;
  workspace_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export const workspacesApi = {
  listWorkspaces: () => fetchApi<WorkspaceItem[]>('/workspaces'),
  getWorkspace: (id: string) => fetchApi<WorkspaceItem>(`/workspaces/${id}`),
  createWorkspace: (name: string) =>
    fetchApi<WorkspaceItem>('/workspaces', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  updateWorkspace: (id: string, name: string) =>
    fetchApi<WorkspaceItem>(`/workspaces/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),
  deleteWorkspace: (id: string) =>
    fetchApi<{ message: string }>(`/workspaces/${id}`, {
      method: 'DELETE',
    }),
  listMembers: (workspaceId: string) =>
    fetchApi<WorkspaceMemberItem[]>(`/workspaces/${workspaceId}/members`),
  addMember: (workspaceId: string, email: string, role = 'MEMBER') =>
    fetchApi<WorkspaceMemberItem>(`/workspaces/${workspaceId}/members`, {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    }),
  updateMemberRole: (workspaceId: string, userId: string, role: string) =>
    fetchApi<WorkspaceMemberItem>(`/workspaces/${workspaceId}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
  removeMember: (workspaceId: string, userId: string) =>
    fetchApi<{ message: string }>(`/workspaces/${workspaceId}/members/${userId}`, {
      method: 'DELETE',
    }),
};
