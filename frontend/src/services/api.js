import axios from 'axios';

// Use proxy in development (same-origin = cookies work), direct URL in production
// The proxy in package.json forwards /api/* to http://localhost:5001/api/*
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for session management
});

// Demo mode status
export const getDemoStatus = async () => {
  const response = await api.get('/demo-status');
  return response.data;
};

// Authentication
export const login = async (username, password) => {
  const response = await api.post('/login', { username, password });
  return response.data;
};

export const register = async (username, email, password) => {
  const response = await api.post('/register', { username, email, password });
  return response.data;
};

export const logout = async () => {
  const response = await api.post('/logout');
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get('/user');
  return response.data;
};

export const updateUserLocation = async (location) => {
  const response = await api.put('/user/location', {
    location
  });
  return response.data;
};

// Plants
export const getPlants = async () => {
  const response = await api.get('/plants');
  return response.data;
};

export const createPlant = async (name, sensorId) => {
  const response = await api.post('/plants', { name, sensor_id: sensorId });
  return response.data;
};

export const deletePlant = async (plantId) => {
  const response = await api.delete(`/plants/${plantId}`);
  return response.data;
};

// Sensor Data
export const fetchSensorData = async (plantId = null) => {
  const params = plantId ? { plant_id: plantId } : {};
  const response = await api.get('/sensor-data', { params });
  return response.data;
};

export const updateSensorData = async (data) => {
  const response = await api.post('/sensor-data', data);
  return response.data;
};

export const getSensorHistory = async (plantId, limit = 20) => {
  const response = await api.get('/sensor-data/history', {
    params: { plant_id: plantId, limit }
  });
  return response.data;
};

// Weather
export const fetchWeather = async (lat = null, lon = null) => {
  try {
    const params = {};
    if (lat !== null && lon !== null) {
      params.lat = lat;
      params.lon = lon;
    }
    const response = await api.get('/weather', { params });
    return response.data;
  } catch (err) {
    // Return error object instead of throwing
    return {
      error: 'Failed to fetch weather',
      message: err.response?.data?.message || err.response?.data?.error || err.message || 'Unable to load weather data'
    };
  }
};

// Predictions
export const fetchPrediction = async (sensorData, weatherData) => {
  const response = await api.post('/predict', {
    sensor: sensorData,
    weather: weatherData,
  });
  return response.data;
};

// Plant Health
export const getPlantHealth = async (plantId) => {
  const response = await api.get(`/plant-health/${plantId}`);
  return response.data;
};

// Chatbot
export const sendChatMessage = async (message, context) => {
  const response = await api.post('/chat', {
    message,
    context
  });
  return response.data;
};

export default api;
