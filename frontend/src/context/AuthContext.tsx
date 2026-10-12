import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { fetchApi } from '../api/client';
import { workspacesApi, WorkspaceItem } from '../api/workspaces';

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  isActive?: boolean;
}

export interface Workspace {
  id: string;
  name: string;
  role?: string;
  owner_id?: string;
  member_count?: number;
}

interface AuthContextType {
  user: User | null;
  activeWorkspace: Workspace | null;
  workspaces: Workspace[];
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void> | void;
  switchWorkspace: (workspaceId: string) => void;
  createWorkspace: (name: string) => Promise<Workspace>;
  refreshWorkspaces: () => Promise<void>;
}

interface ApiUserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface LoginApiResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: ApiUserResponse;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadWorkspacesForUser = useCallback(async (preferredWorkspaceId?: string): Promise<Workspace[]> => {
    try {
      let list = await workspacesApi.listWorkspaces();
      if (!list || list.length === 0) {
        // If user has no workspaces yet, create a default workspace
        const created = await workspacesApi.createWorkspace('Personal Workspace');
        list = [created];
      }

      const mapped: Workspace[] = list.map((w: WorkspaceItem) => ({
        id: w.id,
        name: w.name,
        role: w.current_user_role || 'MEMBER',
        owner_id: w.owner_id,
        member_count: w.member_count,
      }));

      setWorkspaces(mapped);

      const targetId = preferredWorkspaceId || localStorage.getItem('cloudguard_active_workspace_id');
      const selected = mapped.find(w => w.id === targetId) || mapped[0];

      if (selected) {
        setActiveWorkspace(selected);
        localStorage.setItem('cloudguard_active_workspace_id', selected.id);
      } else {
        setActiveWorkspace(null);
      }

      return mapped;
    } catch (err) {
      setWorkspaces([]);
      setActiveWorkspace(null);
      return [];
    }
  }, []);

  // Load current user and workspaces from real backend if token exists
  useEffect(() => {
    let isMounted = true;

    async function loadCurrentSession() {
      const token = localStorage.getItem('cloudguard_token');
      if (!token) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await fetchApi<ApiUserResponse>('/auth/me');
        if (isMounted) {
          setUser({
            id: userData.id,
            name: userData.full_name,
            email: userData.email,
            role: 'ADMIN',
            isActive: userData.is_active,
          });
        }
        if (isMounted) {
          await loadWorkspacesForUser();
        }
      } catch (err) {
        localStorage.removeItem('cloudguard_token');
        localStorage.removeItem('cloudguard_active_workspace_id');
        if (isMounted) {
          setUser(null);
          setWorkspaces([]);
          setActiveWorkspace(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadCurrentSession();

    return () => {
      isMounted = false;
    };
  }, [loadWorkspacesForUser]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await fetchApi<LoginApiResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      localStorage.setItem('cloudguard_token', data.access_token);
      setUser({
        id: data.user.id,
        name: data.user.full_name,
        email: data.user.email,
        role: 'ADMIN',
        isActive: data.user.is_active,
      });

      await loadWorkspacesForUser();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      await fetchApi<ApiUserResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          full_name: name,
          email,
          password,
        }),
      });

      await login(email, password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      const token = localStorage.getItem('cloudguard_token');
      if (token) {
        await fetchApi('/auth/logout', { method: 'POST' });
      }
    } catch (err) {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('cloudguard_token');
      localStorage.removeItem('cloudguard_active_workspace_id');
      setUser(null);
      setWorkspaces([]);
      setActiveWorkspace(null);
    }
  };

  const switchWorkspace = (workspaceId: string) => {
    const found = workspaces.find(w => w.id === workspaceId);
    if (found) {
      setActiveWorkspace(found);
      localStorage.setItem('cloudguard_active_workspace_id', found.id);
    }
  };

  const createWorkspace = async (name: string): Promise<Workspace> => {
    const created = await workspacesApi.createWorkspace(name);
    const newWs: Workspace = {
      id: created.id,
      name: created.name,
      role: created.current_user_role || 'OWNER',
      owner_id: created.owner_id,
      member_count: created.member_count,
    };
    const updated = [...workspaces, newWs];
    setWorkspaces(updated);
    setActiveWorkspace(newWs);
    localStorage.setItem('cloudguard_active_workspace_id', newWs.id);
    return newWs;
  };

  const refreshWorkspaces = async () => {
    await loadWorkspacesForUser(activeWorkspace?.id);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeWorkspace,
        workspaces,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        switchWorkspace,
        createWorkspace,
        refreshWorkspaces,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
