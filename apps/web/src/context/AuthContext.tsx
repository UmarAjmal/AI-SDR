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

export interface RegisterParams {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
  companyName?: string;
  jobTitle?: string;
  workspaceName?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  workspace: AuthWorkspace | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (paramsOrEmail: string | RegisterParams, password?: string, workspaceName?: string) => Promise<void>;
  switchWorkspace: (ws: AuthWorkspace) => void;
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

  // Sync token and workspace ID to Axios headers
  const applyAuthHeaders = (authToken: string | null, wsId: string | null) => {
    if (authToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }

    if (wsId) {
      axios.defaults.headers.common['X-Workspace-Id'] = wsId;
    } else {
      delete axios.defaults.headers.common['X-Workspace-Id'];
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      try {
        const savedToken = localStorage.getItem(TOKEN_KEY);
        const savedUser = localStorage.getItem(USER_KEY);
        const savedWs = localStorage.getItem(WS_KEY);

        if (savedToken && savedUser && savedWs) {
          const parsedWs = JSON.parse(savedWs);
          const parsedUser = JSON.parse(savedUser);

          // Check if token signature is expired
          let isExpired = false;
          try {
            const payload = JSON.parse(atob(savedToken.split('.')[1]));
            if (payload.exp && payload.exp * 1000 <= Date.now()) {
              isExpired = true;
            }
          } catch {
            isExpired = !savedToken.startsWith('demo-');
          }

          if (isExpired && !savedToken.startsWith('demo-')) {
            try {
              const refreshRes = await axios.post('/api/v1/auth/refresh');
              const newAccessToken = refreshRes.data.access_token;
              setToken(newAccessToken);
              setUser(parsedUser);
              setWorkspace(parsedWs);
              localStorage.setItem(TOKEN_KEY, newAccessToken);
              applyAuthHeaders(newAccessToken, parsedWs.id);
            } catch {
              console.warn('Session expired and refresh failed. Clearing credentials.');
              localStorage.removeItem(TOKEN_KEY);
              localStorage.removeItem(USER_KEY);
              localStorage.removeItem(WS_KEY);
              applyAuthHeaders(null, null);
            }
          } else {
            setToken(savedToken);
            setUser(parsedUser);
            setWorkspace(parsedWs);
            applyAuthHeaders(savedToken, parsedWs.id);
          }
        }
      } catch (e) {
        console.error('Failed to restore auth session:', e);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(WS_KEY);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Axios response interceptor for graceful 401 token refresh
  useEffect(() => {
    let isRefreshing = false;
    let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

    const processQueue = (error: any, newToken: string | null = null) => {
      failedQueue.forEach((prom) => {
        if (error) {
          prom.reject(error);
        } else if (newToken) {
          prom.resolve(newToken);
        }
      });
      failedQueue = [];
    };

    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        if (
          error.response?.status === 401 &&
          !originalRequest?._retry &&
          !originalRequest?.url?.includes('/auth/login') &&
          !originalRequest?.url?.includes('/auth/register') &&
          !originalRequest?.url?.includes('/auth/refresh')
        ) {
          if (isRefreshing) {
            return new Promise((resolve, reject) => {
              failedQueue.push({ resolve, reject });
            })
              .then((newTok) => {
                if (originalRequest.headers?.set) {
                  originalRequest.headers.set('Authorization', `Bearer ${newTok}`);
                } else if (originalRequest.headers) {
                  originalRequest.headers['Authorization'] = `Bearer ${newTok}`;
                }
                return axios(originalRequest);
              })
              .catch((err) => Promise.reject(err));
          }

          originalRequest._retry = true;
          isRefreshing = true;

          try {
            const refreshRes = await axios.post('/api/v1/auth/refresh');
            const newAccessToken = refreshRes.data.access_token;
            setToken(newAccessToken);
            localStorage.setItem(TOKEN_KEY, newAccessToken);
            applyAuthHeaders(newAccessToken, workspace?.id || null);

            processQueue(null, newAccessToken);
            if (originalRequest.headers?.set) {
              originalRequest.headers.set('Authorization', `Bearer ${newAccessToken}`);
            } else if (originalRequest.headers) {
              originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
            }
            return axios(originalRequest);
          } catch (refreshErr) {
            processQueue(refreshErr, null);
            return Promise.reject(error);
          } finally {
            isRefreshing = false;
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, [workspace]);

  const switchWorkspace = (ws: AuthWorkspace) => {
    setWorkspace(ws);
    localStorage.setItem(WS_KEY, JSON.stringify(ws));
    if (ws.id) {
      axios.defaults.headers.common['X-Workspace-Id'] = ws.id;
    }
  };

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

      applyAuthHeaders(authToken, authWs.id);
    } catch (err: any) {
      // If backend is unreachable or returns error, rethrow message
      const msg = err.response?.data?.detail || err.message || 'Login failed. Check your credentials.';
      throw new Error(msg);
    }
  };

  const register = async (
    paramsOrEmail: string | RegisterParams,
    passwordParam?: string,
    workspaceNameParam?: string
  ) => {
    try {
      let body: any = {};
      let resolvedWsName = '';
      if (typeof paramsOrEmail === 'string') {
        body = {
          email: paramsOrEmail,
          password: passwordParam,
          workspace_name: workspaceNameParam,
        };
        resolvedWsName = workspaceNameParam || paramsOrEmail.split('@')[0] + "'s Workspace";
      } else {
        body = {
          email: paramsOrEmail.email,
          password: paramsOrEmail.password,
          first_name: paramsOrEmail.firstName,
          last_name: paramsOrEmail.lastName,
          company_name: paramsOrEmail.companyName,
          job_title: paramsOrEmail.jobTitle,
          workspace_name: paramsOrEmail.workspaceName,
        };
        resolvedWsName =
          paramsOrEmail.companyName ||
          (paramsOrEmail.firstName ? `${paramsOrEmail.firstName}'s Workspace` : paramsOrEmail.email.split('@')[0] + "'s Workspace");
      }

      const res = await axios.post('/api/v1/auth/register', body);
      const data = res.data;
      const authToken = data.access_token;
      const authUser: AuthUser = { id: data.user_id, email: body.email };
      const authWs: AuthWorkspace = {
        id: data.active_workspace_id,
        name: resolvedWsName,
        role: data.active_role || 'OWNER',
      };

      setToken(authToken);
      setUser(authUser);
      setWorkspace(authWs);

      localStorage.setItem(TOKEN_KEY, authToken);
      localStorage.setItem(USER_KEY, JSON.stringify(authUser));
      localStorage.setItem(WS_KEY, JSON.stringify(authWs));

      applyAuthHeaders(authToken, authWs.id);
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

    applyAuthHeaders(demoToken, demoWs.id);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setWorkspace(null);

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(WS_KEY);

    applyAuthHeaders(null, null);

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
        switchWorkspace,
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
