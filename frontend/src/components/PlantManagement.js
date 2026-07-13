import React, { useState } from 'react';
import { createPlant, deletePlant } from '../services/api';
import './PlantManagement.css';

const PlantManagement = ({
  plants,
  selectedPlantId,
  onPlantSelect,
  onPlantCreated,
  onPlantDeleted,
  readOnly = false
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [plantName, setPlantName] = useState('');
  const [sensorId, setSensorId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAddPlant = async (e) => {
    e.preventDefault();
    setError('');

    if (!plantName.trim() || !sensorId.trim()) {
      setError('Plant name and sensor ID are required');
      return;
    }

    setLoading(true);
    try {
      const plant = await createPlant(plantName.trim(), sensorId.trim());
      setPlantName('');
      setSensorId('');
      setShowAddForm(false);
      onPlantCreated(plant);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create plant');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePlant = async (plantId) => {
    if (!window.confirm('Are you sure you want to delete this plant?')) {
      return;
    }

    try {
      await deletePlant(plantId);
      onPlantDeleted();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to delete plant');
    }
  };

  return (
    <div className="plant-management">
      <div className="plant-selector">
        <h3>My Plants</h3>
        <div className="plants-list">
          {(Array.isArray(plants) ? plants : []).map(plant => (
            <div
              key={plant.id}
              className={`plant-item ${selectedPlantId === plant.id ? 'active' : ''}`}
              onClick={() => onPlantSelect(plant.id)}
            >
              <span className="plant-name">{plant.name}</span>
              <span className="plant-sensor-id">Sensor: {plant.sensor_id}</span>
              {!readOnly && (
                <button
                  className="delete-plant-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeletePlant(plant.id);
                  }}
                  title="Delete plant"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          {plants.length === 0 && (
            <p className="no-plants">No plants yet. Add one to get started!</p>
          )}
        </div>
        {!readOnly && (
          <button
            className="add-plant-button"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : '+ Add Plant'}
          </button>
        )}
      </div>

      {!readOnly && showAddForm && (
        <div className="add-plant-form">
          <h4>Add New Plant</h4>
          {error && <div className="error-message">{error}</div>}
          <form onSubmit={handleAddPlant}>
            <div className="form-group">
              <label>Plant Name</label>
              <input
                type="text"
                value={plantName}
                onChange={(e) => setPlantName(e.target.value)}
                placeholder="e.g., Basil, Tomato, etc."
                required
              />
            </div>
            <div className="form-group">
              <label>Sensor ID</label>
              <input
                type="text"
                value={sensorId}
                onChange={(e) => setSensorId(e.target.value)}
                placeholder="Unique sensor identifier"
                required
              />
            </div>
            <button type="submit" disabled={loading} className="submit-button">
              {loading ? 'Adding...' : 'Add Plant'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default PlantManagement;

