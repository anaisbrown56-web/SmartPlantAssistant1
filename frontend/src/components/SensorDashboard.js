import React from 'react';
import './SensorDashboard.css';

const SensorDashboard = ({ sensorData, demoEnvironment = false }) => {
  // Only show real data from Neon database (or demo placeholder data)
  if (!sensorData) {
    return (
      <div className="dashboard">
        <div className="no-data-message">Waiting for sensor data from Raspberry Pi...</div>
      </div>
    );
  }

  // Check if data is simulated (shouldn't happen anymore, but double-check)
  // Demo mode intentionally serves placeholder readings
  if (sensorData.is_simulated && !demoEnvironment && !sensorData.is_demo) {
    return (
      <div className="dashboard">
        <div className="no-data-message">Waiting for real sensor data from Raspberry Pi...</div>
      </div>
    );
  }

  // Check if we have real values (not null/undefined)
  const hasRealData = sensorData.light != null && 
                      sensorData.moisture != null && 
                      sensorData.temperature != null;

  if (!hasRealData) {
    return (
      <div className="dashboard">
        <div className="no-data-message">
          {sensorData.message || 'Waiting for sensor data from Raspberry Pi...'}
        </div>
      </div>
    );
  }

  const sourceLabel = 'from Raspberry Pi';

  return (
    <div className="dashboard">
      <div className="card">
        <div className="card-title">
          <span className="status-indicator active"></span>
          Light Level
        </div>
        <div className="card-value">
          {Math.round(sensorData.light)}
          <span className="card-unit"> lux</span>
        </div>
        <div className="card-label">Current ambient light ({sourceLabel})</div>
      </div>

      <div className="card">
        <div className="card-title">
          <span className="status-indicator active"></span>
          Soil Moisture
        </div>
        <div className="card-value">
          {Math.round(sensorData.moisture)}
          <span className="card-unit">%</span>
        </div>
        <div className="card-label">Soil moisture level ({sourceLabel})</div>
      </div>

      <div className="card">
        <div className="card-title">
          <span className="status-indicator active"></span>
          Temperature
        </div>
        <div className="card-value">
          {Math.round(sensorData.temperature)}
          <span className="card-unit">°F</span>
        </div>
        <div className="card-label">Current temperature ({sourceLabel})</div>
      </div>
    </div>
  );
};

export default SensorDashboard;
