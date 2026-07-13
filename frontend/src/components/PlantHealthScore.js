import React, { useState, useEffect } from 'react';
import { getPlantHealth } from '../services/api';
import './PlantHealthScore.css';

const PlantHealthScore = ({ plantId }) => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (plantId) {
      loadHealthData();
      const interval = setInterval(loadHealthData, 30000); // Update every 30 seconds
      return () => clearInterval(interval);
    }
  }, [plantId]);

  const loadHealthData = async () => {
    try {
      const data = await getPlantHealth(plantId);
      setHealthData(data);
      setError(null);
    } catch (err) {
      setError('Failed to load health data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="health-card">
        <div className="loading-text">Calculating health score...</div>
      </div>
    );
  }

  if (error || !healthData) {
    return (
      <div className="health-card">
        <div className="health-header">
          <h3>🌿 Plant Health Score</h3>
        </div>
        <div className="no-health-data">
          {error ? `Error: ${error}` : 'Collecting sensor data... Please wait a moment.'}
        </div>
      </div>
    );
  }

  const { score, status, details, factors, current_values, confidence, probabilities, model_type } = healthData;
  
  // Safety check for current_values
  if (!current_values || !details) {
    return (
      <div className="health-card">
        <div className="health-header">
          <h3>🌿 Plant Health Score</h3>
        </div>
        <div className="no-health-data">
          Collecting initial sensor readings...
        </div>
      </div>
    );
  }
  
  // Determine color based on score
  const getScoreColor = (score) => {
    if (score >= 80) return '#4caf50'; // Green
    if (score >= 65) return '#8bc34a'; // Light green
    if (score >= 50) return '#ff9800'; // Orange
    if (score >= 30) return '#ff5722'; // Deep orange
    return '#f44336'; // Red
  };

  const getStatusIcon = (status) => {
    if (status === 'Excellent') return '🌟';
    if (status === 'Good') return '✅';
    if (status === 'Fair') return '⚠️';
    if (status === 'Poor') return '🔴';
    return '🚨';
  };

  return (
    <div className="health-card">
      <div className="health-header">
        <h3>🌿 Plant Health Score</h3>
        <div className="health-score-main">
          <div 
            className="score-circle"
            style={{ 
              background: `conic-gradient(${getScoreColor(score)} 0deg ${score * 3.6}deg, #e0e0e0 ${score * 3.6}deg 360deg)`
            }}
          >
            <div className="score-inner">
              <span className="score-value">{Math.round(score)}</span>
              <span className="score-max">/100</span>
            </div>
          </div>
          <div className="health-status">
            <span className="status-icon">{getStatusIcon(status)}</span>
            <span className="status-text">{status}</span>
            {confidence !== undefined && (
              <span className="confidence-badge">
                {Math.round(confidence * 100)}% confidence
              </span>
            )}
          </div>
          {model_type && !/demo/i.test(model_type) && (
            <div className="model-type-badge">
              {model_type}
            </div>
          )}
        </div>
      </div>

      <div className="health-details">
        <div className="detail-item">
          <span className="detail-label">Moisture</span>
          <div className="detail-bar">
            <div 
              className="detail-fill" 
              style={{ 
                width: `${(details.moisture_score / 30) * 100}%`,
                backgroundColor: details.moisture_score >= 20 ? '#4caf50' : details.moisture_score >= 10 ? '#ff9800' : '#f44336'
              }}
            ></div>
          </div>
          <span className="detail-value">{(details.moisture_score || 0).toFixed(1)}/30</span>
          <span className="detail-current">({current_values.moisture || 'N/A'}%)</span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Temperature</span>
          <div className="detail-bar">
            <div 
              className="detail-fill" 
              style={{ 
                width: `${((details.temperature_score || 0) / 25) * 100}%`,
                backgroundColor: (details.temperature_score || 0) >= 18 ? '#4caf50' : (details.temperature_score || 0) >= 10 ? '#ff9800' : '#f44336'
              }}
            ></div>
          </div>
          <span className="detail-value">{(details.temperature_score || 0).toFixed(1)}/25</span>
          <span className="detail-current">({current_values.temperature || 'N/A'}°F)</span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Light</span>
          <div className="detail-bar">
            <div 
              className="detail-fill" 
              style={{ 
                width: `${((details.light_score || 0) / 25) * 100}%`,
                backgroundColor: (details.light_score || 0) >= 18 ? '#4caf50' : (details.light_score || 0) >= 10 ? '#ff9800' : '#f44336'
              }}
            ></div>
          </div>
          <span className="detail-value">{(details.light_score || 0).toFixed(1)}/25</span>
          <span className="detail-current">({current_values.light || 'N/A'} lux)</span>
        </div>

        <div className="detail-item">
          <span className="detail-label">Trend</span>
          <div className="detail-bar">
            <div 
              className="detail-fill" 
              style={{ 
                width: `${(details.trend_score / 20) * 100}%`,
                backgroundColor: details.trend_score >= 15 ? '#4caf50' : details.trend_score >= 10 ? '#ff9800' : '#f44336'
              }}
            ></div>
          </div>
          <span className="detail-value">{details.trend_score.toFixed(1)}/20</span>
        </div>
      </div>

      <div className="health-factors">
        <h4>Key Factors:</h4>
        <ul>
          {factors.map((factor, index) => (
            <li key={index}>{factor}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default PlantHealthScore;

