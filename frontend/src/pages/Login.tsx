import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, Mail } from 'lucide-react';
import { Button } from '../components/ui/Button';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      navigate('/app');
    } catch (err: any) {
      setError(err.message || 'Failed to login');
    }
  };

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Shield className="w-12 h-12 text-accent-9 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-content">
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm text-content-secondary">
          Or{' '}
          <Link to="/register" className="font-medium text-accent-9 hover:text-accent-10">
            create a new workspace
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface-1 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-line">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-severity-critical/10 border border-severity-critical/30 rounded-md p-3 text-sm text-severity-critical-ink">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Email address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-content-muted" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 bg-surface-2 border border-line rounded-lg py-2 text-content focus:ring-1 focus:ring-accent-9 focus:border-accent-9 sm:text-sm"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-content-muted" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 bg-surface-2 border border-line rounded-lg py-2 text-content focus:ring-1 focus:ring-accent-9 focus:border-accent-9 sm:text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <Button
                type="submit"
                variant="primary"
                className="w-full flex justify-center py-2.5"
                disabled={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
