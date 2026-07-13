import axios from 'axios';
import { clientDemo, BACKEND_UNAVAILABLE_MESSAGE } from './demoData';

// Use proxy in development (same-origin = cookies work), direct URL in production
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// On Vercel (or any static host) with no API URL configured, never call /api —
// those routes serve index.html and crash the React UI.
const shouldUseClientDemoByDefault =
  process.env.REACT_APP_FORCE_CLIENT_DEMO === 'true' ||
  (!process.env.REACT_APP_API_URL && process.env.NODE_ENV === 'production');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 8000,
});

/** When true, all reads come from client-side demo data (no Flask backend). */
let clientDemoMode = shouldUseClientDemoByDefault;

export const isClientDemoMode = () => clientDemoMode;

export const enableClientDemoMode = () => {
  clientDemoMode = true;
};

const isNetworkFailure = (error) =>
  !error.response ||
  error.code === 'ECONNABORTED' ||
  error.code === 'ERR_NETWORK' ||
  error.message?.includes('Network Error');

/** SPA hosts often return index.html (200) for missing API routes — treat as failure. */
const isInvalidApiPayload = (data) => {
  if (data == null) return true;
  if (typeof data === 'string') {
    const trimmed = data.trim();
    return trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html');
  }
  return false;
};

const ensureJsonObject = (data) => {
  if (isInvalidApiPayload(data) || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('Invalid API response');
  }
  return data;
};

const ensureJsonArray = (data) => {
  if (isInvalidApiPayload(data) || !Array.isArray(data)) {
    throw new Error('Invalid API response');
  }
  return data;
};

// Demo mode status
export const getDemoStatus = async () => {
  if (clientDemoMode) {
    return {
      demo_environment: true,
      client_fallback: true,
      message: 'This data is a placeholder to show how the site works.',
    };
  }
  try {
    const response = await api.get('/demo-status');
    const data = ensureJsonObject(response.data);
    if (typeof data.demo_environment !== 'boolean') {
      throw new Error('Invalid demo-status payload');
    }
    return data;
  } catch (error) {
    clientDemoMode = true;
    return {
      demo_environment: true,
      client_fallback: true,
      message: 'This data is a placeholder to show how the site works.',
    };
  }
};

// Authentication
export const login = async (username, password) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  try {
    const response = await api.post('/login', { username, password });
    return ensureJsonObject(response.data);
  } catch (error) {
    if (error.isBackendUnavailable) throw error;
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
      err.isBackendUnavailable = true;
      throw err;
    }
    throw error;
  }
};

export const register = async (username, email, password) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  try {
    const response = await api.post('/register', { username, email, password });
    return ensureJsonObject(response.data);
  } catch (error) {
    if (error.isBackendUnavailable) throw error;
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
      err.isBackendUnavailable = true;
      throw err;
    }
    throw error;
  }
};

export const logout = async () => {
  if (clientDemoMode) {
    return { message: 'Logged out' };
  }
  try {
    const response = await api.post('/logout');
    return response.data;
  } catch (error) {
    return { message: 'Logged out' };
  }
};

export const getCurrentUser = async () => {
  if (clientDemoMode) {
    throw new Error('Not authenticated');
  }
  const response = await api.get('/user');
  return ensureJsonObject(response.data);
};

export const updateUserLocation = async (location) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  const response = await api.put('/user/location', { location });
  return response.data;
};

// Plants
export const getPlants = async () => {
  if (clientDemoMode) return clientDemo.getPlants();
  try {
    const response = await api.get('/plants');
    return ensureJsonArray(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getPlants();
    }
    throw error;
  }
};

export const createPlant = async (name, sensorId) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  const response = await api.post('/plants', { name, sensor_id: sensorId });
  return response.data;
};

export const deletePlant = async (plantId) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  const response = await api.delete(`/plants/${plantId}`);
  return response.data;
};

// Sensor Data
export const fetchSensorData = async (plantId = null) => {
  if (clientDemoMode) return clientDemo.getSensorData();
  try {
    const params = plantId ? { plant_id: plantId } : {};
    const response = await api.get('/sensor-data', { params });
    return ensureJsonObject(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getSensorData();
    }
    throw error;
  }
};

export const updateSensorData = async (data) => {
  if (clientDemoMode) {
    const err = new Error(BACKEND_UNAVAILABLE_MESSAGE);
    err.isBackendUnavailable = true;
    throw err;
  }
  const response = await api.post('/sensor-data', data);
  return response.data;
};

export const getSensorHistory = async (plantId, limit = 20) => {
  if (clientDemoMode) return clientDemo.getSensorHistory(limit);
  try {
    const response = await api.get('/sensor-data/history', {
      params: { plant_id: plantId, limit },
    });
    return ensureJsonArray(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getSensorHistory(limit);
    }
    throw error;
  }
};

// Weather
export const fetchWeather = async (lat = null, lon = null) => {
  if (clientDemoMode) return clientDemo.getWeather();
  try {
    const params = {};
    if (lat !== null && lon !== null) {
      params.lat = lat;
      params.lon = lon;
    }
    const response = await api.get('/weather', { params });
    return ensureJsonObject(response.data);
  } catch (err) {
    if (isNetworkFailure(err) || err.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getWeather();
    }
    return {
      error: 'Failed to fetch weather',
      message:
        err.response?.data?.message ||
        err.response?.data?.error ||
        err.message ||
        'Unable to load weather data',
    };
  }
};

// Predictions
export const fetchPrediction = async (sensorData, weatherData) => {
  if (clientDemoMode) return clientDemo.getPrediction();
  try {
    const response = await api.post('/predict', {
      sensor: sensorData,
      weather: weatherData,
    });
    return ensureJsonObject(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getPrediction();
    }
    throw error;
  }
};

// Plant Health
export const getPlantHealth = async (plantId) => {
  if (clientDemoMode) return clientDemo.getPlantHealth();
  try {
    const response = await api.get(`/plant-health/${plantId}`);
    return ensureJsonObject(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getPlantHealth();
    }
    throw error;
  }
};

// Chatbot
export const sendChatMessage = async (message, context) => {
  if (clientDemoMode) return clientDemo.getChatReply(message, context);
  try {
    const response = await api.post('/chat', {
      message,
      context,
    });
    return ensureJsonObject(response.data);
  } catch (error) {
    if (isNetworkFailure(error) || error.message === 'Invalid API response') {
      clientDemoMode = true;
      return clientDemo.getChatReply(message, context);
    }
    throw error;
  }
};

export { BACKEND_UNAVAILABLE_MESSAGE };
export default api;
