import React, { createContext, useState, useContext, useEffect } from 'react';
import api, { isClientDemoMode, BACKEND_UNAVAILABLE_MESSAGE } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const isHtmlPayload = (data) =>
  typeof data === 'string' &&
  (data.trim().startsWith('<!DOCTYPE') || data.trim().startsWith('<html'));

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // Static deploys with no backend: skip session check
    if (isClientDemoMode()) {
      setUser(null);
      setIsAuthenticated(false);
      setLoading(false);
      return;
    }

    try {
      const response = await api.get('/user');
      if (isHtmlPayload(response.data) || !response.data?.id) {
        setUser(null);
        setIsAuthenticated(false);
        return;
      }
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    if (isClientDemoMode()) {
      return {
        success: false,
        error: BACKEND_UNAVAILABLE_MESSAGE,
      };
    }

    try {
      const response = await api.post('/login', { username, password });
      if (isHtmlPayload(response.data) || !response.data?.user) {
        return {
          success: false,
          error: BACKEND_UNAVAILABLE_MESSAGE,
        };
      }

      setUser(response.data.user);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const isBackendDown =
        error.isBackendUnavailable ||
        !error.response ||
        error.code === 'ERR_NETWORK' ||
        error.code === 'ECONNABORTED' ||
        isHtmlPayload(error.response?.data);
      const errorMessage = isBackendDown
        ? BACKEND_UNAVAILABLE_MESSAGE
        : (error.response?.data?.error || error.response?.data?.details || error.message || 'Login failed');
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const register = async (username, email, password, location = null) => {
    if (isClientDemoMode()) {
      return {
        success: false,
        error: BACKEND_UNAVAILABLE_MESSAGE,
      };
    }

    try {
      const payload = { username, email, password };
      if (location && location.trim()) {
        payload.location = location.trim();
      }
      const response = await api.post('/register', payload);
      if (isHtmlPayload(response.data) || !response.data?.user) {
        return {
          success: false,
          error: BACKEND_UNAVAILABLE_MESSAGE,
        };
      }

      setUser(response.data.user);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      console.error('Registration error:', error);
      const isBackendDown =
        error.isBackendUnavailable ||
        !error.response ||
        error.code === 'ERR_NETWORK' ||
        error.code === 'ECONNABORTED' ||
        isHtmlPayload(error.response?.data);
      const errorMessage = isBackendDown
        ? BACKEND_UNAVAILABLE_MESSAGE
        : (error.response?.data?.error || error.response?.data?.details || error.message || 'Registration failed');
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const logout = async () => {
    try {
      if (!isClientDemoMode()) {
        await api.post('/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        loading,
        login,
        register,
        logout,
        checkAuth
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
