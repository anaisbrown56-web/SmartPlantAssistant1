import React, { createContext, useState, useContext, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user is already logged in
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await api.get('/user');
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
    try {
      const response = await api.post('/login', { username, password });
      
      // Login was successful - set user state
      setUser(response.data.user);
      setIsAuthenticated(true);
      
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const isBackendDown =
        error.isBackendUnavailable ||
        !error.response ||
        error.code === 'ERR_NETWORK' ||
        error.code === 'ECONNABORTED';
      const errorMessage = isBackendDown
        ? 'The backend is not hooked up to this live deployment yet. We are working on this.'
        : (error.response?.data?.error || error.response?.data?.details || error.message || 'Login failed');
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const register = async (username, email, password, location = null) => {
    try {
      const payload = { username, email, password };
      if (location && location.trim()) {
        payload.location = location.trim();
      }
      const response = await api.post('/register', payload);
      
      setUser(response.data.user);
      setIsAuthenticated(true);
      
      return { success: true };
    } catch (error) {
      console.error('Registration error:', error);
      const isBackendDown =
        error.isBackendUnavailable ||
        !error.response ||
        error.code === 'ERR_NETWORK' ||
        error.code === 'ECONNABORTED';
      const errorMessage = isBackendDown
        ? 'The backend is not hooked up to this live deployment yet. We are working on this.'
        : (error.response?.data?.error || error.response?.data?.details || error.message || 'Registration failed');
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const logout = async () => {
    try {
      await api.post('/logout');
      setUser(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout error:', error);
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

