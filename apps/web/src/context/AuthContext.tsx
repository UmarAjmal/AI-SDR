import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

export interface AuthUser {
  id: string;
  email: string;
}

export interface AuthWorkspace {
  id: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: AuthUser | null;
  workspace: AuthWorkspace | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, workspaceName: string) => Promise<void>;
  loginDemo: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'codenter_auth_token';
const USER_KEY = 'codenter_auth_user';
const WS_KEY = 'codenter_auth_workspace';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [workspace, setWorkspace] = useState<AuthWorkspace | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Sync token to Axios headers
  const applyAuthToken = (authToken: string | null) => {
    if (authToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  };

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedUser = localStorage.getItem(USER_KEY);
      const savedWs = localStorage.getItem(WS_KEY);

      if (savedToken && savedUser && savedWs) {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        setWorkspace(JSON.parse(savedWs));
        applyAuthToken(savedToken);
      }
    } catch (e) {
      console.error('Failed to restore auth session:', e);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(WS_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const res = await axios.post('/api/v1/auth/login', { email, password });
      const data = res.data;
      const authToken = data.access_token;
      const authUser: AuthUser = { id: data.user_id, email };
      const authWs: AuthWorkspace = {
        id: data.active_workspace_id,
        name: email.split('@')[0] + "'s Organization",
        role: data.active_role || 'OWNER',
      };

      setToken(authToken);
      setUser(authUser);
      setWorkspace(authWs);

      localStorage.setItem(TOKEN_KEY, authToken);
      localStorage.setItem(USER_KEY, JSON.stringify(authUser));
      localStorage.setItem(WS_KEY, JSON.stringify(authWs));

      applyAuthToken(authToken);
    } catch (err: any) {
      // If backend is unreachable or returns error, rethrow message
      const msg = err.response?.data?.detail || err.message || 'Login failed. Check your credentials.';
      throw new Error(msg);
    }
  };

  const register = async (email: string, password: string, workspaceName: string) => {
    try {
      const res = await axios.post('/api/v1/auth/register', {
        email,
        password,
        workspace_name: workspaceName,
      });
      const data = res.data;
      const authToken = data.access_token;
      const authUser: AuthUser = { id: data.user_id, email };
      const authWs: AuthWorkspace = {
        id: data.active_workspace_id,
        name: workspaceName,
        role: data.active_role || 'OWNER',
      };

      setToken(authToken);
      setUser(authUser);
      setWorkspace(authWs);

      localStorage.setItem(TOKEN_KEY, authToken);
      localStorage.setItem(USER_KEY, JSON.stringify(authUser));
      localStorage.setItem(WS_KEY, JSON.stringify(authWs));

      applyAuthToken(authToken);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed. Try a different email.';
      throw new Error(msg);
    }
  };

  const loginDemo = () => {
    const demoToken = 'demo-jwt-token-enterprise-sdr';
    const demoUser: AuthUser = {
      id: 'usr-demo-enterprise-01',
      email: 'alex.vance@codenter.ai',
    };
    const demoWs: AuthWorkspace = {
      id: 'ws-784f-9201-enterprise',
      name: 'Enterprise Growth Inc',
      role: 'OWNER',
    };

    setToken(demoToken);
    setUser(demoUser);
    setWorkspace(demoWs);

    localStorage.setItem(TOKEN_KEY, demoToken);
    localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
    localStorage.setItem(WS_KEY, JSON.stringify(demoWs));

    applyAuthToken(demoToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setWorkspace(null);

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(WS_KEY);

    applyAuthToken(null);

    // Call logout endpoint to clear HttpOnly cookie
    axios.post('/api/v1/auth/logout').catch(() => {});
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspace,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        register,
        loginDemo,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
