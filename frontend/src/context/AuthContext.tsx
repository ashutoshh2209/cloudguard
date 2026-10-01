import React, { createContext, useContext, useState, useEffect } from 'react';

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface Workspace {
  id: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  activeWorkspace: Workspace | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock checking auth on initial load
  useEffect(() => {
    const token = localStorage.getItem('cloudguard_token');
    if (token) {
      // Simulate verifying token and getting user/workspace
      setTimeout(() => {
        setUser({
          id: 'u-1',
          name: 'Demo Admin',
          email: 'admin@cloudguard.test',
          role: 'ADMIN'
        });
        setActiveWorkspace({
          id: 'ws-1',
          name: 'Default Workspace'
        });
        setIsLoading(false);
      }, 500);
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 800));
      if (password === 'password') { // any email, password is 'password'
        localStorage.setItem('cloudguard_token', 'mock_jwt_token_123');
        setUser({
          id: 'u-1',
          name: 'Demo Admin',
          email,
          role: 'ADMIN'
        });
        setActiveWorkspace({
          id: 'ws-1',
          name: 'Default Workspace'
        });
      } else {
        throw new Error("Invalid credentials. (Hint: use password='password')");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 800));
      localStorage.setItem('cloudguard_token', 'mock_jwt_token_123');
      setUser({
        id: 'u-2',
        name,
        email,
        role: 'ADMIN'
      });
      setActiveWorkspace({
        id: 'ws-1',
        name: 'Personal Workspace'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('cloudguard_token');
    setUser(null);
    setActiveWorkspace(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeWorkspace,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout
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
