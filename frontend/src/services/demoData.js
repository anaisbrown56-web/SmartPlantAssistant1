/**
 * Client-side demo data for when the Flask backend is unavailable (e.g. Vercel-only deploy).
 * Mirrors backend/demo_data.py so guests still see a working basil dashboard.
 */

const DEMO_PLANT = {
  id: 1,
  name: 'Basil',
  sensor_id: 'demo-basil-001',
  created_at: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(),
};

const RANGES = {
  moisture: [42, 68],
  temperature: [68, 78],
  light: [350, 900],
  weather_temp: [62, 82],
  humidity: [40, 70],
  precipitation: [0, 35],
  windSpeed: [2, 12],
  hours_until_watering: [18, 72],
};

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

const drift = (value, low, high, step = 0.4) => {
  let delta = (Math.random() * 2 - 1) * step;
  const mid = (low + high) / 2;
  delta += (mid - value) * 0.02;
  return clamp(value + delta, low, high);
};

class ClientDemoGenerator {
  constructor() {
    this.moisture = 55;
    this.temperature = 72.5;
    this.light = 580;
    this.weather_temp = 74;
    this.humidity = 55;
    this.precipitation = 10;
    this.wind_speed = 6;
    this.hours_until_watering = 42;
    this._tick = 0;
    this._history = this._seedHistory(24);
  }

  _seedHistory(n) {
    const history = [];
    let moisture = 58;
    let temperature = 71;
    let light = 520;
    const now = Date.now();
    for (let i = 0; i < n; i += 1) {
      moisture = drift(moisture, ...RANGES.moisture, 1.2);
      temperature = drift(temperature, ...RANGES.temperature, 0.5);
      const hourFactor = Math.sin((i / n) * Math.PI);
      light = clamp(400 + hourFactor * 400 + (Math.random() * 80 - 40), ...RANGES.light);
      history.push({
        light: Math.round(light * 10) / 10,
        moisture: Math.round(moisture * 10) / 10,
        temperature: Math.round(temperature * 10) / 10,
        timestamp: new Date(now - 5 * 60 * 1000 * (n - i)).toISOString(),
      });
    }
    this.moisture = moisture;
    this.temperature = temperature;
    this.light = light;
    return history;
  }

  _advance() {
    this._tick += 1;
    this.moisture = drift(this.moisture, ...RANGES.moisture, 0.8);
    this.temperature = drift(this.temperature, ...RANGES.temperature, 0.35);
    const phase = (this._tick % 60) / 60;
    const baseLight = 450 + 350 * Math.sin(phase * Math.PI);
    this.light = clamp(baseLight + (Math.random() * 60 - 30), ...RANGES.light);
    this.weather_temp = drift(this.weather_temp, ...RANGES.weather_temp, 0.4);
    this.humidity = drift(this.humidity, ...RANGES.humidity, 0.8);
    this.precipitation = drift(this.precipitation, ...RANGES.precipitation, 1.5);
    this.wind_speed = drift(this.wind_speed, ...RANGES.windSpeed, 0.4);
    this.hours_until_watering = drift(
      this.hours_until_watering,
      ...RANGES.hours_until_watering,
      1.2
    );

    const reading = {
      light: Math.round(this.light * 10) / 10,
      moisture: Math.round(this.moisture * 10) / 10,
      temperature: Math.round(this.temperature * 10) / 10,
      timestamp: new Date().toISOString(),
    };
    this._history.push(reading);
    this._history = this._history.slice(-48);
    return reading;
  }

  getPlants() {
    return [{ ...DEMO_PLANT }];
  }

  getSensorData() {
    const reading = this._advance();
    return {
      plant_id: DEMO_PLANT.id,
      plant_name: DEMO_PLANT.name,
      light: reading.light,
      moisture: reading.moisture,
      temperature: reading.temperature,
      timestamp: reading.timestamp,
      is_simulated: false,
      is_demo: true,
    };
  }

  getSensorHistory(limit = 20) {
    this._advance();
    return this._history.slice(-limit);
  }

  getWeather() {
    this.weather_temp = drift(this.weather_temp, ...RANGES.weather_temp, 0.25);
    this.humidity = drift(this.humidity, ...RANGES.humidity, 0.5);
    this.precipitation = drift(this.precipitation, ...RANGES.precipitation, 0.8);
    this.wind_speed = drift(this.wind_speed, ...RANGES.windSpeed, 0.25);
    const forecasts = ['Partly Cloudy', 'Mostly Sunny', 'Sunny', 'Scattered Clouds', 'Clear'];
    const forecast = forecasts[this._tick % forecasts.length];
    return {
      temperature: Math.round(this.weather_temp * 10) / 10,
      humidity: Math.round(this.humidity * 10) / 10,
      precipitation: Math.round(this.precipitation * 10) / 10,
      windSpeed: Math.round(this.wind_speed * 10) / 10,
      forecast,
      description: `${forecast}. Conditions look suitable for an indoor basil setup near a bright window.`,
      timestamp: new Date().toISOString(),
      is_demo: true,
    };
  }

  getPrediction() {
    const hours = Math.round(this.hours_until_watering * 10) / 10;
    let recommendation = 'Watering not needed yet';
    if (hours < 24) recommendation = 'Water soon';
    else if (hours < 48) recommendation = 'Water within 2 days';
    else if (hours < 72) recommendation = 'Water within 3 days';
    return {
      modelType: 'Demo Placeholder',
      hasMoistureData: true,
      hoursUntilWatering: hours,
      recommendation,
      timestamp: new Date().toISOString(),
      is_demo: true,
    };
  }

  getPlantHealth() {
    const moisture = this.moisture;
    const temperature = this.temperature;
    const light = this.light;

    let moisture_score = 0;
    if (moisture >= 40 && moisture <= 70) moisture_score = 30;
    else if ((moisture >= 30 && moisture < 40) || (moisture > 70 && moisture <= 80)) moisture_score = 20;
    else if ((moisture >= 20 && moisture < 30) || (moisture > 80 && moisture <= 90)) moisture_score = 10;

    let temperature_score = 10;
    if (temperature >= 65 && temperature <= 80) temperature_score = 25;
    else if ((temperature >= 60 && temperature < 65) || (temperature > 80 && temperature <= 85)) {
      temperature_score = 18;
    }

    let light_score = 10;
    if (light >= 300 && light <= 800) light_score = 25;
    else if ((light >= 200 && light < 300) || (light > 800 && light <= 1000)) light_score = 18;

    const trend_score = 18;
    const score = Math.round((moisture_score + temperature_score + light_score + trend_score) * 10) / 10;
    let status = 'Needs Attention';
    if (score >= 80) status = 'Excellent';
    else if (score >= 65) status = 'Good';
    else if (score >= 50) status = 'Fair';

    return {
      score,
      status,
      confidence: 0.92,
      model_type: 'Demo Placeholder',
      details: {
        moisture_score,
        temperature_score,
        light_score,
        trend_score,
      },
      factors: [
        'Soil moisture is in a healthy range for basil.',
        'Temperature suits indoor herb growth.',
        'Light levels look good for a sunny windowsill.',
      ],
      current_values: {
        moisture: Math.round(moisture * 10) / 10,
        temperature: Math.round(temperature * 10) / 10,
        light: Math.round(light * 10) / 10,
      },
      is_demo: true,
    };
  }

  getChatReply(message, context = {}) {
    const sensor = context.sensorData || {};
    const weather = context.weatherData || {};
    const health = context.healthData || {};
    const prediction = context.prediction || {};
    const plantName = context.plantName || 'Basil';
    const trends = context.trends || {};

    const moisture = sensor.moisture ?? Math.round(this.moisture * 10) / 10;
    const temperature = sensor.temperature ?? Math.round(this.temperature * 10) / 10;
    const light = sensor.light ?? Math.round(this.light * 10) / 10;
    const healthScore = health.score ?? this.getPlantHealth().score;
    const healthStatus = health.status ?? this.getPlantHealth().status;
    const hours = prediction.hoursUntilWatering ?? this.getPrediction().hoursUntilWatering;
    const recommendation = prediction.recommendation ?? this.getPrediction().recommendation;
    const weatherTemp = weather.temperature ?? Math.round(this.weather_temp * 10) / 10;
    const humidity = weather.humidity ?? Math.round(this.humidity * 10) / 10;
    const forecast = weather.forecast || 'Partly Cloudy';
    const msg = (message || '').toLowerCase();

    let reply;
    if (/(water|moisture|dry|thirsty)/.test(msg)) {
      reply = `Your ${plantName} soil moisture is at ${moisture}%. Based on that, watering is suggested in about ${hours} hours (${recommendation.toLowerCase()}). For basil, aim to keep moisture roughly in the mid-40s to mid-60s.`;
    } else if (/(light|sun|bright)/.test(msg)) {
      const ok = light >= 300 && light <= 800;
      reply = `Light on your ${plantName} is currently ${light} lux. Basil likes a bright windowsill—roughly 300–800 lux is a good indoor target. ${ok ? 'That looks solid right now.' : 'You may want to move it closer to a brighter window.'}`;
    } else if (/(temp|hot|cold|heat|weather)/.test(msg)) {
      reply = `Plant temperature is ${temperature}°F, and outdoor weather is about ${weatherTemp}°F with ${humidity}% humidity (${forecast}). Basil is happiest around 65–80°F indoors.`;
    } else if (/(health|score|how is|how's|status)/.test(msg)) {
      reply = `Your ${plantName} health score is ${healthScore}/100 (${healthStatus}). Latest readings: moisture ${moisture}%, temperature ${temperature}°F, light ${light} lux. Watering outlook: ${recommendation.toLowerCase()} (~${hours} hours).`;
    } else {
      let trendNote = '';
      if (trends.moistureTrend != null) {
        const delta = trends.moistureTrend;
        const direction = delta > 0.5 ? 'rising' : delta < -0.5 ? 'falling' : 'steady';
        trendNote = ` Moisture has been ${direction} recently (${delta > 0 ? '+' : ''}${delta.toFixed(1)}%).`;
      }
      reply = `Here's a quick snapshot of your ${plantName}: moisture ${moisture}%, temperature ${temperature}°F, light ${light} lux, health ${healthScore}/100 (${healthStatus}). Watering prediction: ${recommendation} (~${hours} hours).${trendNote}`;
    }

    return {
      message: reply,
      timestamp: new Date().toISOString(),
      is_demo: true,
    };
  }
}

export const clientDemo = new ClientDemoGenerator();

export const BACKEND_UNAVAILABLE_MESSAGE =
  'Account sign-in is unavailable in this preview. Live authentication will be available in a future update.';
