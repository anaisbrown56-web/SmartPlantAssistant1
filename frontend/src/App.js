import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';
import { getDemoStatus } from './services/api';
import './App.css';

function AppContent() {
  const { isAuthenticated, loading } = useAuth();
  const [showRegister, setShowRegister] = useState(false);
  const [demoEnvironment, setDemoEnvironment] = useState(false);
  const [demoStatusLoaded, setDemoStatusLoaded] = useState(false);
  const [forceLogin, setForceLogin] = useState(false);

  useEffect(() => {
    // Prefer client demo immediately in production with no API URL
    getDemoStatus()
      .then((data) => setDemoEnvironment(!!data?.demo_environment || !!data?.client_fallback))
      .catch(() => setDemoEnvironment(true))
      .finally(() => setDemoStatusLoaded(true));
  }, []);

  if (loading || !demoStatusLoaded) {
    return (
      <div className="app-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  // Guest demo: no login required when DEMO_ENVIRONMENT is on
  if (demoEnvironment && !isAuthenticated && !forceLogin) {
    return (
      <Dashboard
        isGuestDemo
        demoEnvironment
        onSignIn={() => setForceLogin(true)}
      />
    );
  }

  if (!isAuthenticated) {
    return showRegister ? (
      <Register onSwitchToLogin={() => setShowRegister(false)} />
    ) : (
      <Login
        onSwitchToRegister={() => setShowRegister(true)}
        demoEnvironment={demoEnvironment}
        onBackToDemo={demoEnvironment ? () => setForceLogin(false) : null}
      />
    );
  }

  return <Dashboard demoEnvironment={demoEnvironment} />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
