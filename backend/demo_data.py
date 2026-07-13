"""
Demo/placeholder data for when DEMO_ENVIRONMENT=true.
Generates realistic drifting basil plant readings so the UI works without sensors.
"""
import math
import random
from datetime import datetime, timedelta, timezone

DEMO_PLANT = {
    'id': 1,
    'name': 'Basil',
    'sensor_id': 'demo-basil-001',
    'created_at': (datetime.now(timezone.utc) - timedelta(days=21)).isoformat(),
}

# Realistic indoor basil ranges
RANGES = {
    'moisture': (42.0, 68.0),
    'temperature': (68.0, 78.0),
    'light': (350.0, 900.0),
    'weather_temp': (62.0, 82.0),
    'humidity': (40.0, 70.0),
    'precipitation': (0.0, 35.0),
    'windSpeed': (2.0, 12.0),
    'hours_until_watering': (18.0, 72.0),
}


def _clamp(value, low, high):
    return max(low, min(high, value))


def _drift(value, low, high, step=0.4):
    """Small random walk kept within range."""
    delta = random.uniform(-step, step)
    # Soft pull toward the middle so values stay believable
    mid = (low + high) / 2
    delta += (mid - value) * 0.02
    return _clamp(value + delta, low, high)


class DemoDataGenerator:
    """Stateful generator so successive polls show slight drift."""

    def __init__(self):
        self.moisture = 55.0
        self.temperature = 72.5
        self.light = 580.0
        self.weather_temp = 74.0
        self.humidity = 55.0
        self.precipitation = 10.0
        self.wind_speed = 6.0
        self.hours_until_watering = 42.0
        self._tick = 0
        self._history = self._seed_history(24)

    def _seed_history(self, n):
        history = []
        moisture, temperature, light = 58.0, 71.0, 520.0
        now = datetime.now(timezone.utc)
        for i in range(n):
            moisture = _drift(moisture, *RANGES['moisture'], step=1.2)
            temperature = _drift(temperature, *RANGES['temperature'], step=0.5)
            # Light follows a gentle day curve plus noise
            hour_factor = math.sin((i / n) * math.pi)
            light = _clamp(400 + hour_factor * 400 + random.uniform(-40, 40), *RANGES['light'])
            ts = now - timedelta(minutes=5 * (n - i))
            history.append({
                'light': round(light, 1),
                'moisture': round(moisture, 1),
                'temperature': round(temperature, 1),
                'timestamp': ts.isoformat(),
            })
        self.moisture = moisture
        self.temperature = temperature
        self.light = light
        return history

    def _advance(self):
        self._tick += 1
        self.moisture = _drift(self.moisture, *RANGES['moisture'], step=0.8)
        self.temperature = _drift(self.temperature, *RANGES['temperature'], step=0.35)
        # Mild diurnal light oscillation
        phase = (self._tick % 60) / 60.0
        base_light = 450 + 350 * math.sin(phase * math.pi)
        self.light = _clamp(base_light + random.uniform(-30, 30), *RANGES['light'])
        self.weather_temp = _drift(self.weather_temp, *RANGES['weather_temp'], step=0.4)
        self.humidity = _drift(self.humidity, *RANGES['humidity'], step=0.8)
        self.precipitation = _drift(self.precipitation, *RANGES['precipitation'], step=1.5)
        self.wind_speed = _drift(self.wind_speed, *RANGES['windSpeed'], step=0.4)
        self.hours_until_watering = _drift(
            self.hours_until_watering, *RANGES['hours_until_watering'], step=1.2
        )

        reading = {
            'light': round(self.light, 1),
            'moisture': round(self.moisture, 1),
            'temperature': round(self.temperature, 1),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(reading)
        self._history = self._history[-48:]
        return reading

    def get_plant(self):
        return dict(DEMO_PLANT)

    def get_plants(self):
        return [self.get_plant()]

    def get_sensor_data(self):
        reading = self._advance()
        return {
            'plant_id': DEMO_PLANT['id'],
            'plant_name': DEMO_PLANT['name'],
            'light': reading['light'],
            'moisture': reading['moisture'],
            'temperature': reading['temperature'],
            'timestamp': reading['timestamp'],
            'is_simulated': False,
            'is_demo': True,
            'demo_message': 'This data is a placeholder to show how the site works.',
        }

    def get_sensor_history(self, limit=20):
        # Advance once so charts tick forward on refresh
        self._advance()
        return self._history[-limit:]

    def get_weather(self):
        self.weather_temp = _drift(self.weather_temp, *RANGES['weather_temp'], step=0.25)
        self.humidity = _drift(self.humidity, *RANGES['humidity'], step=0.5)
        self.precipitation = _drift(self.precipitation, *RANGES['precipitation'], step=0.8)
        self.wind_speed = _drift(self.wind_speed, *RANGES['windSpeed'], step=0.25)

        forecasts = [
            'Partly Cloudy',
            'Mostly Sunny',
            'Sunny',
            'Scattered Clouds',
            'Clear',
        ]
        forecast = forecasts[self._tick % len(forecasts)]
        return {
            'temperature': round(self.weather_temp, 1),
            'humidity': round(self.humidity, 1),
            'precipitation': round(self.precipitation, 1),
            'windSpeed': round(self.wind_speed, 1),
            'forecast': forecast,
            'description': (
                f'{forecast}. Conditions look suitable for an indoor basil setup near a bright window.'
            ),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'is_demo': True,
        }

    def get_prediction(self):
        hours = round(self.hours_until_watering, 1)
        if hours < 24:
            recommendation = 'Water soon'
        elif hours < 48:
            recommendation = 'Water within 2 days'
        elif hours < 72:
            recommendation = 'Water within 3 days'
        else:
            recommendation = 'Watering not needed yet'
        return {
            'modelType': 'Demo Placeholder',
            'hasMoistureData': True,
            'hoursUntilWatering': hours,
            'recommendation': recommendation,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'is_demo': True,
        }

    def get_plant_health(self):
        moisture = self.moisture
        temperature = self.temperature
        light = self.light

        if 40 <= moisture <= 70:
            moisture_score = 30.0
        elif 30 <= moisture < 40 or 70 < moisture <= 80:
            moisture_score = 20.0
        elif 20 <= moisture < 30 or 80 < moisture <= 90:
            moisture_score = 10.0
        else:
            moisture_score = 0.0

        if 65 <= temperature <= 80:
            temperature_score = 25.0
        elif 60 <= temperature < 65 or 80 < temperature <= 85:
            temperature_score = 18.0
        else:
            temperature_score = 10.0

        if 300 <= light <= 800:
            light_score = 25.0
        elif 200 <= light < 300 or 800 < light <= 1000:
            light_score = 18.0
        else:
            light_score = 10.0

        trend_score = 18.0
        score = round(moisture_score + temperature_score + light_score + trend_score, 1)

        if score >= 80:
            status = 'Excellent'
        elif score >= 65:
            status = 'Good'
        elif score >= 50:
            status = 'Fair'
        else:
            status = 'Needs Attention'

        return {
            'score': score,
            'status': status,
            'confidence': 0.92,
            'model_type': 'Demo Placeholder',
            'details': {
                'moisture_score': moisture_score,
                'temperature_score': temperature_score,
                'light_score': light_score,
                'trend_score': trend_score,
            },
            'factors': [
                'Soil moisture is in a healthy range for basil.',
                'Temperature suits indoor herb growth.',
                'Light levels look good for a sunny windowsill.',
            ],
            'current_values': {
                'moisture': round(moisture, 1),
                'temperature': round(temperature, 1),
                'light': round(light, 1),
            },
            'is_demo': True,
        }

    def get_chat_reply(self, message, context=None):
        """Context-aware demo chatbot that mirrors the same placeholder plant data."""
        context = context or {}
        sensor = context.get('sensorData') or {}
        weather = context.get('weatherData') or {}
        health = context.get('healthData') or {}
        prediction = context.get('prediction') or {}
        plant_name = context.get('plantName') or 'Basil'
        trends = context.get('trends') or {}

        # Fall back to live demo generator state so replies stay in sync
        moisture = sensor.get('moisture')
        if moisture is None:
            moisture = round(self.moisture, 1)
        temperature = sensor.get('temperature')
        if temperature is None:
            temperature = round(self.temperature, 1)
        light = sensor.get('light')
        if light is None:
            light = round(self.light, 1)

        health_score = health.get('score')
        health_status = health.get('status')
        if health_score is None:
            demo_health = self.get_plant_health()
            health_score = demo_health['score']
            health_status = demo_health['status']

        hours = prediction.get('hoursUntilWatering')
        recommendation = prediction.get('recommendation')
        if hours is None:
            demo_pred = self.get_prediction()
            hours = demo_pred['hoursUntilWatering']
            recommendation = demo_pred['recommendation']

        weather_temp = weather.get('temperature', round(self.weather_temp, 1))
        humidity = weather.get('humidity', round(self.humidity, 1))
        forecast = weather.get('forecast', 'Partly Cloudy')

        msg = (message or '').lower()

        if any(word in msg for word in ('water', 'moisture', 'dry', 'thirsty')):
            reply = (
                f"Your {plant_name} soil moisture is at **{moisture}%**. "
                f"Based on that, watering is suggested in about **{hours} hours** "
                f"({recommendation.lower()}). "
                f"For basil, aim to keep moisture roughly in the mid-40s to mid-60s."
            )
        elif any(word in msg for word in ('light', 'sun', 'bright')):
            reply = (
                f"Light on your {plant_name} is currently **{light} lux**. "
                f"Basil likes a bright windowsill—roughly 300–800 lux is a good indoor target. "
                f"{'That looks solid right now.' if 300 <= float(light) <= 800 else 'You may want to move it closer to a brighter window.'}"
            )
        elif any(word in msg for word in ('temp', 'hot', 'cold', 'heat', 'weather')):
            reply = (
                f"Plant temperature is **{temperature}°F**, and outdoor weather is about "
                f"**{weather_temp}°F** with **{humidity}%** humidity ({forecast}). "
                f"Basil is happiest around 65–80°F indoors."
            )
        elif any(word in msg for word in ('health', 'score', 'how is', "how's", 'status')):
            reply = (
                f"Your {plant_name} health score is **{health_score}/100** ({health_status}). "
                f"Latest readings: moisture {moisture}%, temperature {temperature}°F, light {light} lux. "
                f"Watering outlook: {recommendation.lower()} (~{hours} hours)."
            )
        else:
            trend_note = ''
            if trends.get('moistureTrend') is not None:
                delta = trends['moistureTrend']
                direction = 'rising' if delta > 0.5 else 'falling' if delta < -0.5 else 'steady'
                trend_note = f" Moisture has been {direction} recently ({delta:+.1f}%)."

            reply = (
                f"Here's a quick snapshot of your {plant_name}: "
                f"moisture **{moisture}%**, temperature **{temperature}°F**, light **{light} lux**, "
                f"health **{health_score}/100** ({health_status}). "
                f"Watering prediction: **{recommendation}** (~{hours} hours).{trend_note}"
            )

        # Strip markdown bold for plain UI display consistency with existing chatbot
        reply = reply.replace('**', '')

        return {
            'message': reply,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'is_demo': True,
        }


demo_generator = DemoDataGenerator()
