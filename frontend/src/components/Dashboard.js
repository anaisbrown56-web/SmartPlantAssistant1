import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchSensorData,
  fetchWeather,
  fetchPrediction,
  getPlants,
  getSensorHistory,
  getPlantHealth
} from '../services/api';
import SensorDashboard from './SensorDashboard';
import WeatherSection from './WeatherSection';
import PredictionCard from './PredictionCard';
import LightChart from './LightChart';
import MoistureChart from './MoistureChart';
import TemperatureChart from './TemperatureChart';
import PredictionChart from './PredictionChart';
import PlantManagement from './PlantManagement';
import PlantHealthScore from './PlantHealthScore';
import Chatbot from './Chatbot';
import LocationSettings from './LocationSettings';
import './Dashboard.css';

const Dashboard = ({ isGuestDemo = false, demoEnvironment = false, onSignIn = null }) => {
  const { user, logout } = useAuth();
  const [sensorData, setSensorData] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [predictionHistory, setPredictionHistory] = useState([]);
  const [plants, setPlants] = useState([]);
  const [selectedPlantId, setSelectedPlantId] = useState(null);
  const [selectedPlant, setSelectedPlant] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPlants();
  }, []);

  useEffect(() => {
    if (plants.length > 0 && !selectedPlantId) {
      setSelectedPlantId(plants[0].id);
    }
  }, [plants, selectedPlantId]);

  useEffect(() => {
    if (selectedPlantId) {
      // Reset prediction history when switching plants
      setPredictionHistory([]);
      loadData();
      const interval = setInterval(loadData, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedPlantId]);

  useEffect(() => {
    // Weather will be loaded with user's saved location or geolocation
    updateWeather();
  }, []);

  const loadPlants = async () => {
    try {
      const plantsData = await getPlants();
      setPlants(plantsData);
      if (plantsData.length === 0) {
        setError('No plants found. Please add a plant first.');
        setLoading(false);
      } else {
        setError(null);
      }
    } catch (err) {
      console.error('Error loading plants:', err);
      setError('Failed to load plants');
      setLoading(false);
    }
  };

  const loadData = async () => {
    if (!selectedPlantId) return;

    try {
      setError(null);
      const [sensor, historyData] = await Promise.all([
        fetchSensorData(selectedPlantId),
        getSensorHistory(selectedPlantId, 20)
      ]);

      setSensorData(sensor);
      setSelectedPlant(plants.find(p => p.id === selectedPlantId));
      
      // Only update history if data actually changed (compare timestamps)
      setHistory(prev => {
        const newHistory = historyData.map(h => ({
          ...h,
          timestamp: new Date(h.timestamp),
          prediction: null // Will be updated with prediction
        }));
        
        // Check if the latest timestamp is different
        const prevLatest = prev.length > 0 ? prev[prev.length - 1]?.timestamp?.getTime() : null;
        const newLatest = newHistory.length > 0 ? newHistory[newHistory.length - 1]?.timestamp?.getTime() : null;
        
        // Only update if we have new data (different latest timestamp)
        if (prevLatest !== newLatest) {
          return newHistory;
        }
        return prev; // No change, return previous state
      });

      // Get weather if not loaded
      if (!weatherData) {
        await updateWeather();
      }

      // Get prediction - try even if sensor data is missing (weather-only prediction)
      if (weatherData) {
        try {
          const pred = await fetchPrediction(sensor || {}, weatherData);
          setPrediction(pred);
          
          // Add prediction to history if it's significantly different from the last one
          const predictionValue = pred.hoursUntilWatering || pred.wateringFrequencyDays;
          if (predictionValue != null) {
            setPredictionHistory(prev => {
              const lastPrediction = prev.length > 0 ? prev[prev.length - 1] : null;
              const lastValue = lastPrediction?.prediction;
              
              // Only add if it's different by more than 5% or if it's the first prediction
              const shouldAdd = !lastValue || 
                Math.abs(predictionValue - lastValue) > Math.max(0.05 * lastValue, 1);
              
              if (shouldAdd) {
                const newEntry = {
                  timestamp: new Date(),
                  prediction: predictionValue,
                  hasMoistureData: pred.hasMoistureData || false
                };
                // Keep only last 50 predictions
                const updated = [...prev, newEntry].slice(-50);
                return updated;
              }
              return prev;
            });
          }
        } catch (err) {
          console.error('Error fetching prediction:', err);
          setPrediction(null);
        }
      }
      
      // Get health data if we have sensor data
      if (sensor) {
        try {
          const health = await getPlantHealth(selectedPlantId);
          setHealthData(health);
        } catch (err) {
          // No health data yet - that's okay for new plants
          setHealthData(null);
        }
      }

      setLoading(false);
    } catch (err) {
      console.error('Error loading data:', err);
      setError(err.response?.data?.error || err.message);
      setLoading(false);
    }
  };

  const updateWeather = async (lat = null, lon = null) => {
    try {
      const weather = await fetchWeather(lat, lon);
      
      // Only update weather if it's significantly different (to prevent constant prediction changes)
      const shouldUpdate = !weatherData || 
        Math.abs((weatherData.temperature || 0) - (weather.temperature || 0)) > 2 ||
        Math.abs((weatherData.humidity || 0) - (weather.humidity || 0)) > 5 ||
        Math.abs((weatherData.precipitation || 0) - (weather.precipitation || 0)) > 10;
      
      if (shouldUpdate) {
        setWeatherData(weather);

        // Update prediction whenever weather updates (even without sensor data)
        try {
          const pred = await fetchPrediction(sensorData || {}, weather);
          setPrediction(pred);
          
          // Add prediction to history if it's significantly different from the last one
          const predictionValue = pred.hoursUntilWatering || pred.wateringFrequencyDays;
          if (predictionValue != null) {
            setPredictionHistory(prev => {
              const lastPrediction = prev.length > 0 ? prev[prev.length - 1] : null;
              const lastValue = lastPrediction?.prediction;
              
              // Only add if it's different by more than 5% or if it's the first prediction
              const shouldAdd = !lastValue || 
                Math.abs(predictionValue - lastValue) > Math.max(0.05 * lastValue, 1);
              
              if (shouldAdd) {
                const newEntry = {
                  timestamp: new Date(),
                  prediction: predictionValue,
                  hasMoistureData: pred.hasMoistureData || false
                };
                // Keep only last 50 predictions
                const updated = [...prev, newEntry].slice(-50);
                return updated;
              }
              return prev;
            });
          }
        } catch (err) {
          console.error('Error updating prediction:', err);
        }
      }
    } catch (err) {
      console.error('Error updating weather:', err);
    }
  };

  const handlePlantCreated = async (plant) => {
    await loadPlants();
    setSelectedPlantId(plant.id);
  };

  const handlePlantDeleted = async () => {
    await loadPlants();
    if (plants.length > 1) {
      const remainingPlants = await getPlants();
      if (remainingPlants.length > 0) {
        setSelectedPlantId(remainingPlants[0].id);
      } else {
        setSelectedPlantId(null);
        setError('No plants found. Please add a plant first.');
      }
    } else {
      setSelectedPlantId(null);
      setSensorData(null);
      setHistory([]);
      setPredictionHistory([]);
      setError('No plants found. Please add a plant first.');
    }
  };

  if (loading && plants.length === 0) {
    return (
      <div className="app-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="header">
        <div className="header-content">
          <div className="header-logo-section">
            <img 
              src="/logo.png" 
              alt="S-PLANT Pledge Project" 
              className="header-logo"
            />
          </div>
          <div className="user-info">
            <span>{isGuestDemo ? 'Guest · Basil demo' : `Welcome, ${user?.username}`}</span>
            {isGuestDemo ? (
              onSignIn && (
                <button onClick={onSignIn} className="logout-button">Sign in</button>
              )
            ) : (
              <button onClick={logout} className="logout-button">Logout</button>
            )}
          </div>
        </div>
      </div>

      <PlantManagement
        plants={plants}
        selectedPlantId={selectedPlantId}
        onPlantSelect={setSelectedPlantId}
        onPlantCreated={handlePlantCreated}
        onPlantDeleted={handlePlantDeleted}
        readOnly={isGuestDemo || demoEnvironment}
      />

      {error && plants.length === 0 && (
        <div className="error-banner">{error}</div>
      )}

      {selectedPlantId && (
        <div className="content">
          {/* Sensor Data - Full Width Horizontal Row */}
          <SensorDashboard sensorData={sensorData} demoEnvironment={demoEnvironment} />

          {/* Main Dashboard Grid */}
          <div className="main-dashboard-grid">
            {/* Left Column: Weather */}
            <div className="left-column">
              <WeatherSection weatherData={weatherData} />
            </div>

            {/* Right Column: Plant Health and Prediction */}
            <div className="right-column">
              <PlantHealthScore plantId={selectedPlantId} />
              <PredictionCard prediction={prediction} />
            </div>
          </div>

          {/* Charts Section */}
          <div className="charts-section">
            <div className="sensor-charts-grid">
              <LightChart history={history} />
              <MoistureChart history={history} />
              <TemperatureChart history={history} />
            </div>
            <PredictionChart history={predictionHistory} />
          </div>

          {/* Chatbot Section */}
          <div className="chatbot-section">
            <Chatbot 
              sensorData={sensorData}
              weatherData={weatherData}
              healthData={healthData}
              plantName={selectedPlant?.name}
              prediction={prediction}
              history={history}
            />
          </div>
        </div>
      )}

      {/* Location Settings at Bottom — hide for guests in demo */}
      {!isGuestDemo && <LocationSettings />}

      {demoEnvironment && (
        <div className="demo-banner demo-banner-bottom" role="status">
          This data is a placeholder to show how the site works.
        </div>
      )}
    </div>
  );
};

export default Dashboard;

