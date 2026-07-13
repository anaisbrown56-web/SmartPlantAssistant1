import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const Login = ({ onSwitchToRegister, demoEnvironment = false, onBackToDemo = null }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);
    setLoading(false);

    if (!result.success) {
      setError(result.error);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-wrapper">
        <div className="auth-card">
          <div className="auth-header-section">
            <h1>🌱 Smart Plant Assistant</h1>
            <p className="auth-subtitle">Monitor your plants with AI-powered insights</p>
          </div>
          
          <div className="auth-form-section">
            <h2>Welcome Back</h2>
            <form onSubmit={handleSubmit}>
              {error && <div className="error-message">{error}</div>}
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                  placeholder="Enter your username"
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="Enter your password"
                />
              </div>
              <button type="submit" disabled={loading} className="auth-button">
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </form>
            <p className="auth-switch">
              Don't have an account?{' '}
              <button type="button" onClick={onSwitchToRegister} className="link-button">
                Create Account
              </button>
            </p>
            {demoEnvironment && onBackToDemo && (
              <p className="auth-switch">
                <button type="button" onClick={onBackToDemo} className="link-button">
                  ← Back to basil demo
                </button>
              </p>
            )}
          </div>

          <div className="auth-info-section">
            <h3>Features</h3>
            <ul className="auth-features">
              <li>📊 Real-time sensor monitoring</li>
              <li>🌤️ Weather data integration</li>
              <li>💧 AI-powered watering predictions</li>
              <li>📈 Plant health scoring</li>
              <li>💬 AI chatbot assistant</li>
            </ul>
            <div className="auth-test-account">
              <p><strong>Test Account:</strong></p>
              <p>Username: <code>testuser</code></p>
              <p>Password: <code>testpass123</code></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

