import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../services/api';
import './Chatbot.css';

const Chatbot = ({ 
  sensorData = null, 
  weatherData = null, 
  healthData = null, 
  plantName = null,
  prediction = null,
  history = []
}) => {
  const isDemo = !!(sensorData?.is_demo);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: isDemo
        ? `Hello! I'm your Plant Care Assistant for ${plantName || 'Basil'}. I can see the live demo readings on this page and will answer using those numbers. Ask me about moisture, light, health, or watering.`
        : `Hello! I'm your Smart Plant Assistant chatbot. I can help you understand your plant's health, sensor readings, and provide care recommendations. How can I assist you today?`
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Log when context data updates (for debugging)
  useEffect(() => {
    if (sensorData?.timestamp) {
      console.log('Chatbot context updated with latest sensor data:', sensorData.timestamp);
    }
  }, [sensorData, weatherData, healthData, prediction]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      // Prepare comprehensive context with latest data
      const context = {
        sensorData: sensorData || {},
        weatherData: weatherData || {},
        healthData: healthData || {},
        plantName: plantName || 'Unknown',
        prediction: prediction || {},
        // Include recent sensor history trends (last 5 readings)
        recentHistory: history.slice(-5).map(h => ({
          timestamp: h.timestamp,
          moisture: h.moisture,
          temperature: h.temperature,
          light: h.light
        })),
        // Calculate trends from recent history (comparing last 5 readings)
        trends: (() => {
          const recent = history.slice(-5);
          if (recent.length >= 2) {
            const first = recent[0];
            const last = recent[recent.length - 1];
            return {
              moistureTrend: (last?.moisture || 0) - (first?.moisture || 0),
              temperatureTrend: (last?.temperature || 0) - (first?.temperature || 0),
              lightTrend: (last?.light || 0) - (first?.light || 0)
            };
          }
          return null;
        })(),
        // Timestamp of latest reading
        lastReadingTime: sensorData?.timestamp || (history.length > 0 ? history[history.length - 1]?.timestamp : null)
      };

      const response = await sendChatMessage(userMessage, context);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.message || response.content || 'Sorry, I encountered an error.'
      }]);
    } catch (error) {
      console.error('Chatbot error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h3>💬 Plant Care Assistant</h3>
        <span className="chatbot-status">{isDemo ? 'Synced to demo data' : 'AI-powered'}</span>
      </div>
      <div className="chatbot-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <span className="typing-indicator">...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form className="chatbot-input-form" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your plant's health, watering, or care tips..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
};

export default Chatbot;

