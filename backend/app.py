from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests
import numpy as np
from datetime import datetime, timezone
import os
import secrets
from demo_data import demo_generator
# Load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    # Look for .env in the project root (parent of backend directory)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        print(f'Loaded environment variables from {env_path}')
    else:
        print(f'.env file not found at {env_path}, using system environment variables')
except ImportError:
    print('python-dotenv not installed. Install with: pip install python-dotenv')
    print('Using system environment variables only.')

app = Flask(__name__)
# DEMO_ENVIRONMENT: when true, serve drifting placeholder basil data and allow guest viewing
DEMO_ENVIRONMENT = os.environ.get('DEMO_ENVIRONMENT', 'false').strip().lower() in ('true', '1', 'yes')
if DEMO_ENVIRONMENT:
    print('🎭 DEMO_ENVIRONMENT=true — serving placeholder basil demo data (guest access enabled)')
else:
    print('✅ DEMO_ENVIRONMENT=false — using live sensor/database data')

# SECRET_KEY must be consistent across app restarts for sessions to work
# If not set in .env, use a fixed development key (change in production!)
SECRET_KEY_ENV = os.environ.get('SECRET_KEY')
if SECRET_KEY_ENV:
    app.config['SECRET_KEY'] = SECRET_KEY_ENV
else:
    # Fixed dev key - sessions will persist across restarts
    # IMPORTANT: Set SECRET_KEY in .env for production!
    app.config['SECRET_KEY'] = 'dev-secret-key-fixed-for-sessions-please-change-in-production-2024'
# Database configuration - supports SQLite (local) and Postgres (Neon)
# For Neon Postgres: Set DATABASE_URL in .env file
# Format: postgresql://user:password@host:port/dbname?sslmode=require
# For SQLite (local dev): Leave DATABASE_URL unset or use sqlite:///smart_plant.db
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Postgres (Neon) - ensure SSL mode is set
    if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
        # Add sslmode=require if not present (required for Neon)
        if 'sslmode=' not in database_url:
            separator = '&' if '?' in database_url else '?'
            database_url = f"{database_url}{separator}sslmode=require"
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f'✅ Using Postgres database (Neon)')
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f'✅ Using custom database: {database_url[:50]}...')
else:
    # Default to SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_plant.db'
    print('✅ Using SQLite database (local development)')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
# For localhost cross-port, use 'None' with Secure=False (development only)
# Browsers treat localhost as same-site, but explicit setting helps
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 'Lax' works for localhost cross-port
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_DOMAIN'] = None  # None allows cookies for localhost
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_NAME'] = 'session'  # Explicit cookie name
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Enable CORS with credentials for session cookies
CORS(app, 
     supports_credentials=True, 
     origins=['http://localhost:3000', 'http://localhost:3001'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     expose_headers=['Set-Cookie'],
     allow_credentials=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None  # Don't redirect for API

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access - return 401 for API"""
    return jsonify({'error': 'Authentication required'}), 401

def login_required_unless_demo(f):
    """Require login unless DEMO_ENVIRONMENT is enabled (guest demo viewing)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if DEMO_ENVIRONMENT:
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            return unauthorized()
        return f(*args, **kwargs)
    return decorated_function

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(200), default='New York, NY')  # City/Place name
    latitude = db.Column(db.Float, default=40.7128)  # Default to NYC
    longitude = db.Column(db.Float, default=-74.0060)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plants = db.relationship('Plant', backref='owner', lazy=True, cascade='all, delete-orphan')

class Plant(db.Model):
    __tablename__ = 'plants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sensor_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique sensor identifier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sensor_readings = db.relationship('SensorReading', backref='plant', lazy=True, cascade='all, delete-orphan')

class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=False)
    light = db.Column(db.Float, nullable=False)
    moisture = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login"""
    try:
        user = db.session.get(User, int(user_id))
        print(f'DEBUG load_user: Loading user_id={user_id}, found={user is not None}')
        return user
    except (ValueError, TypeError) as e:
        print(f'DEBUG load_user: Error loading user_id={user_id}: {e}')
        return None
    except Exception as e:
        print(f'DEBUG load_user: Unexpected error loading user_id={user_id}: {e}')
        return None

# ML Model - Random Forest Regressor for Watering Prediction
try:
    from ml_model import WateringPredictionModel
    # Initialize the Random Forest model
    # It will load from disk if available, otherwise use fallback predictions
    ml_model = WateringPredictionModel()
    print('✅ ML watering model loaded successfully')
except Exception as e:
    print(f'⚠️  Warning: Could not load ML watering model: {e}')
    print('   Using fallback prediction model')
    import traceback
    traceback.print_exc()
    # Create a simple fallback model
    class FallbackModel:
        def predict(self, features):
            # Simple fallback - return 72 hours
            return 72.0
        is_trained = False
    ml_model = FallbackModel()

# ML Model - Random Forest Classifier for Health Classification
try:
    from health_model import PlantHealthClassifier
    # Initialize the health classifier
    # It will load from disk if available, otherwise use fallback predictions
    health_classifier = PlantHealthClassifier()
    print('✅ ML health classifier loaded successfully')
except Exception as e:
    print(f'⚠️  Warning: Could not load ML health classifier: {e}')
    print('   Using fallback rule-based health calculation')
    import traceback
    traceback.print_exc()
    health_classifier = None

# NWS API User-Agent (required for API access)
NWS_USER_AGENT = os.environ.get('NWS_USER_AGENT', 'SmartPlantAssistant-tyler.i.hughes@vanderbilt.edu')
NWS_HEADERS = {'User-Agent': NWS_USER_AGENT}

# Authentication Routes
def geocode_location(location_name):
    """Convert a place name to latitude/longitude using Nominatim (OpenStreetMap)"""
    try:
        if not location_name or not location_name.strip():
            return None, None
        
        # Use Nominatim geocoding service (free, no API key needed)
        geocode_url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': location_name,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': NWS_USER_AGENT  # Respectful use of free service
        }
        
        response = requests.get(geocode_url, params=params, headers=headers, timeout=10)
        
        if response.ok:
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                lat = float(result.get('lat', 0))
                lon = float(result.get('lon', 0))
                return lat, lon
        
        return None, None
    except Exception as e:
        print(f'Geocoding error: {e}')
        return None, None

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        location = data.get('location')  # Place name (e.g., "Nashville, TN")
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not username or not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Handle location - prefer place name, fallback to coordinates, then default
        if location and location.strip():
            # Geocode the place name
            lat, lon = geocode_location(location)
            if lat and lon:
                latitude = lat
                longitude = lon
            else:
                return jsonify({'error': f'Could not find location: {location}. Please try a more specific location (e.g., "City, State" or "City, Country")'}), 400
        elif latitude is not None and longitude is not None:
            # Use provided coordinates
            latitude = float(latitude)
            longitude = float(longitude)
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return jsonify({'error': 'Invalid coordinates'}), 400
            location = f"{latitude:.4f}, {longitude:.4f}"  # Create a simple location string
        else:
            # No default location - user must set it later
            location = None
            latitude = None
            longitude = None

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            location=location,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(user)
        db.session.commit()

        # Login the user immediately after registration
        login_user(user, remember=True)
        session.permanent = True  # Make session persistent
        
        response = jsonify({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'location': user.location,
                'latitude': user.latitude,
                'longitude': user.longitude
            }
        })
        
        print(f'DEBUG register: Registered user {user.id}, session keys={list(session.keys())}')
        print(f'DEBUG register: _user_id in session={session.get("_user_id")}')
        
        return response, 201

    except ValueError as e:
        print(f'Registration ValueError: {e}')
        return jsonify({'error': 'Invalid location or coordinates'}), 400
    except Exception as e:
        db.session.rollback()
        print(f'Registration error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            # Ensure session is saved and persistent
            session.permanent = True
            
            print(f'DEBUG login: Logged in user {user.id}, session keys={list(session.keys())}')
            print(f'DEBUG login: _user_id in session={session.get("_user_id")}')
            
            # Build user response safely (handle None values)
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email or '',
                'location': getattr(user, 'location', None) or '',
                'latitude': getattr(user, 'latitude', None),
                'longitude': getattr(user, 'longitude', None)
            }
            
            # Convert None to None (JSON null), but ensure numeric types
            if user_data['latitude'] is None:
                user_data['latitude'] = None
            if user_data['longitude'] is None:
                user_data['longitude'] = None
            
            response = jsonify({
                'message': 'Login successful',
                'user': user_data
            })
            
            # Explicitly set cookie attributes to ensure they're sent
            print(f'DEBUG login: Response headers before: {list(response.headers.keys())}')
            
            return response
        else:
            print(f'DEBUG login: Invalid credentials for username: {username}')
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        print(f'Login error [{error_type}]: {error_message}')
        import traceback
        print('=' * 70)
        print('FULL TRACEBACK:')
        traceback.print_exc()
        print('=' * 70)
        return jsonify({
            'error': 'Login failed',
            'error_type': error_type,
            'details': error_message
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'demo_environment': DEMO_ENVIRONMENT,
    })

@app.route('/api/demo-status', methods=['GET'])
def demo_status():
    """Whether the server is running in demo/placeholder mode."""
    return jsonify({
        'demo_environment': DEMO_ENVIRONMENT,
        'message': (
            'This data is a placeholder to show how the site works.'
            if DEMO_ENVIRONMENT else None
        ),
    })

@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    """Debug endpoint to check session status"""
    return jsonify({
        'session_keys': list(session.keys()),
        'user_id': session.get('_user_id'),
        'permanent': session.permanent,
        'is_authenticated': current_user.is_authenticated if current_user else False,
        'user': {
            'id': current_user.id,
            'username': current_user.username
        } if current_user and current_user.is_authenticated else None,
        'cookies_received': list(request.cookies.keys())
    })

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged in user"""
    try:
        return jsonify({
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email or '',
            'location': getattr(current_user, 'location', None) or '',
            'latitude': getattr(current_user, 'latitude', None),
            'longitude': getattr(current_user, 'longitude', None)
        })
    except Exception as e:
        print(f'Error in get_current_user: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get user data', 'details': str(e)}), 500

@app.route('/api/user/location', methods=['PUT'])
@login_required
def update_user_location():
    """Update user's location by place name or coordinates"""
    try:
        data = request.json
        location = data.get('location')  # Place name
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Prefer place name over coordinates
        if location and location.strip():
            lat, lon = geocode_location(location)
            if lat and lon:
                current_user.location = location
                current_user.latitude = lat
                current_user.longitude = lon
                db.session.commit()
                
                return jsonify({
                    'message': 'Location updated successfully',
                    'location': current_user.location,
                    'latitude': current_user.latitude,
                    'longitude': current_user.longitude
                })
            else:
                return jsonify({'error': f'Could not find location: {location}. Please try a more specific location.'}), 400
        
        # Fallback to coordinates if provided
        elif latitude is not None and longitude is not None:
            latitude = float(latitude)
            longitude = float(longitude)
            
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return jsonify({'error': 'Invalid coordinates'}), 400
            
            current_user.latitude = latitude
            current_user.longitude = longitude
            current_user.location = f"{latitude:.4f}, {longitude:.4f}"
            db.session.commit()
            
            return jsonify({
                'message': 'Location updated successfully',
                'location': current_user.location,
                'latitude': current_user.latitude,
                'longitude': current_user.longitude
            })
        else:
            return jsonify({'error': 'Location name or coordinates are required'}), 400
            
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Plant Management Routes
@app.route('/api/plants', methods=['GET'])
@login_required_unless_demo
def get_plants():
    """Get all plants for current user (or demo basil plant)."""
    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_plants())

    plants = Plant.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': plant.id,
        'name': plant.name,
        'sensor_id': plant.sensor_id,
        'created_at': plant.created_at.isoformat()
    } for plant in plants])

@app.route('/api/plants', methods=['POST'])
@login_required
def create_plant():
    """Create a new plant"""
    try:
        # Debug: Check authentication status
        print(f'DEBUG create_plant: current_user={current_user}, is_authenticated={current_user.is_authenticated if current_user else False}')
        print(f'DEBUG create_plant: cookies={dict(request.cookies)}')
        print(f'DEBUG create_plant: session={dict(session)}')
        
        data = request.json
        name = data.get('name')
        sensor_id = data.get('sensor_id')

        if not name or not sensor_id:
            return jsonify({'error': 'Name and sensor_id required'}), 400

        if Plant.query.filter_by(sensor_id=sensor_id).first():
            return jsonify({'error': 'Sensor ID already in use'}), 400

        plant = Plant(
            name=name,
            sensor_id=sensor_id,
            user_id=current_user.id
        )
        db.session.add(plant)
        db.session.commit()

        return jsonify({
            'id': plant.id,
            'name': plant.name,
            'sensor_id': plant.sensor_id,
            'created_at': plant.created_at.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f'Create plant error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/plants/<int:plant_id>', methods=['DELETE'])
@login_required
def delete_plant(plant_id):
    """Delete a plant"""
    plant = Plant.query.filter_by(id=plant_id, user_id=current_user.id).first()
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404

    db.session.delete(plant)
    db.session.commit()
    return jsonify({'message': 'Plant deleted successfully'})

# Sensor Data Routes
@app.route('/api/sensor-data', methods=['GET'])
@login_required_unless_demo
def get_sensor_data():
    """Get current sensor data for user's plants (or demo placeholder data)."""
    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_sensor_data())

    plant_id = request.args.get('plant_id', type=int)
    
    if plant_id:
        # Get specific plant's data
        plant = Plant.query.filter_by(id=plant_id, user_id=current_user.id).first()
        if not plant:
            return jsonify({'error': 'Plant not found'}), 404
        
        # Get latest reading from Neon database
        latest_reading = SensorReading.query.filter_by(plant_id=plant_id)\
            .order_by(SensorReading.timestamp.desc()).first()
        
        if latest_reading:
            return jsonify({
                'plant_id': plant_id,
                'plant_name': plant.name,
                'light': latest_reading.light,
                'moisture': latest_reading.moisture,
                'temperature': latest_reading.temperature,
                'timestamp': latest_reading.timestamp.isoformat(),
                'is_simulated': False  # Real sensor data from Neon
            })
        else:
            # No readings yet - return null instead of simulated data
            # Frontend will show "No data available" message
            return jsonify({
                'plant_id': plant_id,
                'plant_name': plant.name,
                'light': None,
                'moisture': None,
                'temperature': None,
                'timestamp': None,
                'is_simulated': False,
                'message': 'No sensor readings available yet. Waiting for data from Raspberry Pi.'
            })
    else:
        # Get all plants' data
        plants = Plant.query.filter_by(user_id=current_user.id).all()
        if not plants:
            return jsonify({'error': 'No plants found. Please add a plant first.'}), 404
        
        # Return first plant's data by default
        plant = plants[0]
        latest_reading = SensorReading.query.filter_by(plant_id=plant.id)\
            .order_by(SensorReading.timestamp.desc()).first()
        
        if latest_reading:
            return jsonify({
                'plant_id': plant.id,
                'plant_name': plant.name,
                'light': latest_reading.light,
                'moisture': latest_reading.moisture,
                'temperature': latest_reading.temperature,
                'timestamp': latest_reading.timestamp.isoformat(),
                'is_simulated': False  # Real sensor data from Neon
            })
        else:
            # No readings yet - return null instead of simulated data
            return jsonify({
                'plant_id': plant.id,
                'plant_name': plant.name,
                'light': None,
                'moisture': None,
                'temperature': None,
                'timestamp': None,
                'is_simulated': False,
                'message': 'No sensor readings available yet. Waiting for data from Raspberry Pi.'
            })

@app.route('/api/sensor-data', methods=['POST'])
@login_required
def update_sensor_data():
    """Update sensor data from actual sensor"""
    try:
        data = request.json
        sensor_id = data.get('sensor_id')
        plant_id = data.get('plant_id')
        
        # Find plant by sensor_id or plant_id
        if sensor_id:
            plant = Plant.query.filter_by(sensor_id=sensor_id, user_id=current_user.id).first()
        elif plant_id:
            plant = Plant.query.filter_by(id=plant_id, user_id=current_user.id).first()
        else:
            return jsonify({'error': 'sensor_id or plant_id required'}), 400
        
        if not plant:
            return jsonify({'error': 'Plant not found'}), 404
        
        # Create new sensor reading
        reading = SensorReading(
            plant_id=plant.id,
            light=data.get('light', 0),
            moisture=data.get('moisture', 0),
            temperature=data.get('temperature', 0)
        )
        db.session.add(reading)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'plant_id': plant.id,
                'plant_name': plant.name,
                'light': reading.light,
                'moisture': reading.moisture,
                'temperature': reading.temperature,
                'timestamp': reading.timestamp.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensor-data/history', methods=['GET'])
@login_required_unless_demo
def get_sensor_history():
    """Get sensor reading history"""
    plant_id = request.args.get('plant_id', type=int)
    limit = request.args.get('limit', 20, type=int)

    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_sensor_history(limit=limit))
    
    if not plant_id:
        return jsonify({'error': 'plant_id required'}), 400
    
    plant = Plant.query.filter_by(id=plant_id, user_id=current_user.id).first()
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    
    readings = SensorReading.query.filter_by(plant_id=plant_id)\
        .order_by(SensorReading.timestamp.desc()).limit(limit).all()
    
    return jsonify([{
        'light': r.light,
        'moisture': r.moisture,
        'temperature': r.temperature,
        'timestamp': r.timestamp.isoformat()
    } for r in reversed(readings)])


@app.route('/api/weather', methods=['GET'])
@login_required_unless_demo
def get_weather():
    """Fetch weather data from NWS API (or demo placeholder weather)."""
    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_weather())

    try:
        # Use user's saved location, or request params (no fake defaults)
        lat = request.args.get('lat') or current_user.latitude
        lon = request.args.get('lon') or current_user.longitude
        
        if lat is None or lon is None:
            return jsonify({
                'error': 'Location not set',
                'message': 'Please set your location in Location Settings to fetch weather data.'
            }), 400
        
        lat = float(lat)
        lon = float(lon)
        
        grid_url = f'https://api.weather.gov/points/{lat},{lon}'
        grid_response = requests.get(grid_url, headers=NWS_HEADERS, timeout=10)
        
        if not grid_response.ok:
            raise Exception('Failed to get grid point')
        
        grid_data = grid_response.json()
        forecast_url = grid_data['properties']['forecast']
        
        forecast_response = requests.get(forecast_url, headers=NWS_HEADERS, timeout=10)
        if not forecast_response.ok:
            raise Exception('Failed to get forecast')
        
        forecast_data = forecast_response.json()
        current_period = forecast_data['properties']['periods'][0]
        
        observation_data = None
        try:
            observation_url = grid_data['properties']['observationStations']
            stations_response = requests.get(observation_url, headers=NWS_HEADERS, timeout=10)
            
            if stations_response.ok:
                stations_data = stations_response.json()
                if stations_data.get('features') and len(stations_data['features']) > 0:
                    station_id = stations_data['features'][0]['properties']['stationIdentifier']
                    obs_response = requests.get(
                        f'https://api.weather.gov/stations/{station_id}/observations/latest',
                        headers=NWS_HEADERS,
                        timeout=10
                    )
                    if obs_response.ok:
                        observation_data = obs_response.json()
        except Exception as e:
            print(f'Could not fetch observations: {e}')
        
        temp = current_period['temperature']  # This is already in Fahrenheit from forecast
        humidity = current_period.get('relativeHumidity', {}).get('value')  # Try forecast first
        
        # Get more accurate data from observations if available
        if observation_data and observation_data.get('properties'):
            props = observation_data['properties']
            if props.get('temperature') and props['temperature'].get('value'):
                # NWS observation temperature is in Celsius, convert to Fahrenheit
                temp_celsius = props['temperature']['value']
                if temp_celsius is not None:
                    temp = (temp_celsius * 9/5) + 32
            # Prefer observation humidity if available
            if props.get('relativeHumidity') and props['relativeHumidity'].get('value') is not None:
                humidity = props['relativeHumidity']['value']
        
        # If humidity is not available, return None (don't use fake fallback)
        # Frontend will handle missing humidity gracefully
        
        # Get wind speed - ALWAYS use forecast wind speed (not observation)
        # The forecast wind speed is in format like "5 to 10 mph" or "8 mph"
        forecast_wind_str = current_period.get('windSpeed', '5 mph')
        wind_speed = _parse_wind_speed(forecast_wind_str)
        
        print(f'[WEATHER] Using forecast wind: "{forecast_wind_str}" -> {wind_speed} mph')
        
        # Ignore observation wind speed - it can be inaccurate or from a different time
        
        weather = {
            'temperature': round(temp, 1),
            'humidity': round(humidity, 1) if humidity is not None else None,
            'precipitation': current_period.get('probabilityOfPrecipitation', {}).get('value', 0),
            'windSpeed': round(wind_speed, 1),
            'forecast': current_period.get('shortForecast', 'Unknown'),
            'description': current_period.get('detailedForecast', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(weather)
        
    except Exception as e:
        print(f'Error fetching weather: {e}')
        # Return error instead of fake fallback data
        return jsonify({
            'error': 'Unable to fetch weather data. Please check your location settings and try again.',
            'message': 'Weather data temporarily unavailable.'
        }), 503

def _parse_wind_speed(wind_string):
    """Parse wind speed from NWS format (e.g., '5 to 10 mph', '5-10 mph', 'Calm', '8 mph')"""
    try:
        import re
        # Handle "Calm" or empty
        if not wind_string or wind_string.lower() in ['calm', 'none', '']:
            return 0.0
        
        # Convert to string if not already
        wind_str = str(wind_string).strip()
        
        # Extract numbers from string like "5 to 10 mph", "5-10 mph", or "8 mph"
        numbers = re.findall(r'\d+(?:\.\d+)?', wind_str)
        if numbers:
            # If range like "5 to 10" or "5-10", take the average
            if len(numbers) >= 2:
                avg = (float(numbers[0]) + float(numbers[1])) / 2
                print(f'Parsed wind range {wind_str} -> average: {avg} mph')
                return avg
            else:
                value = float(numbers[0])
                print(f'Parsed wind speed {wind_str} -> {value} mph')
                return value
    except Exception as e:
        print(f'Error parsing wind speed: {e}, string: {wind_string}')
    print(f'Using default wind speed 5.0 mph for: {wind_string}')
    return 5.0  # Default reasonable wind speed

@app.route('/api/predict', methods=['POST'])
@login_required_unless_demo
def predict_watering():
    """Predict when to water based on sensor and weather data using Random Forest"""
    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_prediction())

    try:
        data = request.json
        sensor = data.get('sensor', {})
        weather = data.get('weather', {})
        
        # Extract features for prediction model
        # If moisture data is available, use it; otherwise use weather-only
        sensor_temp = sensor.get('temperature', weather.get('temperature', 72))
        humidity = weather.get('humidity', 60)
        precipitation = weather.get('precipitation', 0)
        
        # Check if we have REAL moisture sensor data (not simulated)
        # Simulated data has is_simulated=True flag, or we check if it's from database
        sensor_is_simulated = sensor.get('is_simulated', False)
        moisture = sensor.get('moisture')
        has_moisture = moisture is not None and not sensor_is_simulated  # Only count real moisture data
        
        if has_moisture:
            # Use all 4 features: [moisture, temperature, humidity, precipitation]
            features = [moisture, sensor_temp, humidity, precipitation]
            # Predict hours until watering
            prediction_result = ml_model.predict(features)
            hours_until = float(prediction_result) if isinstance(prediction_result, (int, float)) else None
            frequency_days = None
        else:
            # Weather-only: [temperature, humidity, precipitation]
            features = [sensor_temp, humidity, precipitation]
            # Predict watering frequency (days)
            prediction_result = ml_model.predict(features)
            if isinstance(prediction_result, dict):
                frequency_days = prediction_result.get('frequency_days')
                hours_until = prediction_result.get('hours_until')
            else:
                frequency_days = float(prediction_result)
                hours_until = None
        
        # Build response
        response = {
            'modelType': 'Random Forest' if ml_model.is_trained else 'Weather-Based',
            'hasMoistureData': has_moisture,
            'timestamp': datetime.now().isoformat()
        }
        
        if has_moisture and hours_until is not None:
            # Has moisture data - return hours until watering
            response['hoursUntilWatering'] = round(hours_until, 1)
            response['recommendation'] = get_watering_recommendation(hours_until)
        elif frequency_days is not None:
            # No moisture data - return watering frequency
            response['wateringFrequencyDays'] = round(frequency_days, 1)
            response['recommendation'] = get_watering_frequency_recommendation(frequency_days)
        
        return jsonify(response)
        
    except Exception as e:
        print(f'Prediction error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'hoursUntilWatering': 72,
            'modelType': 'Error'
        }), 500

def get_watering_recommendation(hours):
    """Get human-readable watering recommendation based on hours until watering"""
    if hours < 24:
        return 'Water soon'
    elif hours < 48:
        return 'Water within 2 days'
    elif hours < 72:
        return 'Water within 3 days'
    else:
        return 'Watering not needed yet'

def get_watering_frequency_recommendation(frequency_days):
    """Get human-readable watering frequency recommendation"""
    if frequency_days < 1.5:
        return f'Water every {round(frequency_days * 24)} hours'
    elif frequency_days < 2.5:
        return f'Water every {round(frequency_days)} days'
    elif frequency_days < 4:
        return f'Water every {round(frequency_days)} days'
    else:
        return f'Water every {round(frequency_days)} days'

def calculate_plant_health_score(plant_id):
    """
    Calculate plant health score (0-100) based on sensor readings
    
    Formula Components:
    1. Moisture Score (0-30 points):
       - Optimal: 40-70% = 30 points
       - Good: 30-40% or 70-80% = 20 points
       - Fair: 20-30% or 80-90% = 10 points
       - Poor: <20% or >90% = 0 points
    
    2. Temperature Score (0-25 points):
       - Optimal: 65-80°F = 25 points
       - Good: 60-65°F or 80-85°F = 18 points
       - Fair: 55-60°F or 85-90°F = 10 points
       - Poor: <55°F or >90°F = 0 points
    
    3. Light Score (0-25 points):
       - Optimal: 300-800 lux = 25 points
       - Good: 200-300 lux or 800-1000 lux = 18 points
       - Fair: 100-200 lux or 1000-1500 lux = 10 points
       - Poor: <100 lux or >1500 lux = 0 points
    
    4. Trend Score (0-20 points):
       - Based on recent 5 readings
       - Stable/improving conditions = 20 points
       - Slight decline = 15 points
       - Moderate decline = 10 points
       - Rapid decline = 5 points
    
    Total Health Score = Moisture + Temperature + Light + Trend
    """
    # Get recent readings
    recent_readings = SensorReading.query.filter_by(plant_id=plant_id)\
        .order_by(SensorReading.timestamp.desc()).limit(5).all()
    
    if not recent_readings:
        return {
            'score': 50,  # Default if no data
            'status': 'Unknown',
            'details': {
                'moisture_score': 0,
                'temperature_score': 0,
                'light_score': 0,
                'trend_score': 10
            },
            'factors': ['No sensor data available']
        }
    
    latest = recent_readings[0]
    
    # 1. Moisture Score (0-30 points)
    moisture = latest.moisture
    if 40 <= moisture <= 70:
        moisture_score = 30
        moisture_status = 'optimal'
    elif 30 <= moisture < 40 or 70 < moisture <= 80:
        moisture_score = 20
        moisture_status = 'good'
    elif 20 <= moisture < 30 or 80 < moisture <= 90:
        moisture_score = 10
        moisture_status = 'fair'
    else:
        moisture_score = 0
        moisture_status = 'poor'
    
    # 2. Temperature Score (0-25 points)
    temp = latest.temperature
    if 65 <= temp <= 80:
        temp_score = 25
        temp_status = 'optimal'
    elif 60 <= temp < 65 or 80 < temp <= 85:
        temp_score = 18
        temp_status = 'good'
    elif 55 <= temp < 60 or 85 < temp <= 90:
        temp_score = 10
        temp_status = 'fair'
    else:
        temp_score = 0
        temp_status = 'poor'
    
    # 3. Light Score (0-25 points)
    light = latest.light
    if 300 <= light <= 800:
        light_score = 25
        light_status = 'optimal'
    elif 200 <= light < 300 or 800 < light <= 1000:
        light_score = 18
        light_status = 'good'
    elif 100 <= light < 200 or 1000 < light <= 1500:
        light_score = 10
        light_status = 'fair'
    else:
        light_score = 0
        light_status = 'poor'
    
    # 4. Trend Score (0-20 points) - Analyze recent trend
    trend_score = 20
    if len(recent_readings) >= 3:
        # Calculate average change rates
        moisture_changes = []
        temp_changes = []
        
        for i in range(len(recent_readings) - 1):
            prev = recent_readings[i + 1]
            curr = recent_readings[i]
            
            # Moisture declining is bad
            moisture_changes.append(curr.moisture - prev.moisture)
            # Temperature stability is good
            temp_changes.append(abs(curr.temperature - prev.temperature))
        
        avg_moisture_change = sum(moisture_changes) / len(moisture_changes)
        avg_temp_stability = 10 - (sum(temp_changes) / len(temp_changes))
        
        # Moisture declining rapidly
        if avg_moisture_change < -5:
            trend_score -= 10
        elif avg_moisture_change < -2:
            trend_score -= 5
        
        # Temperature unstable
        if avg_temp_stability < 5:
            trend_score -= 5
        
        trend_score = max(0, min(20, trend_score))
    
    # Calculate total score
    total_score = moisture_score + temp_score + light_score + trend_score
    total_score = max(0, min(100, total_score))
    
    # Determine status
    if total_score >= 80:
        status = 'Excellent'
    elif total_score >= 65:
        status = 'Good'
    elif total_score >= 50:
        status = 'Fair'
    elif total_score >= 30:
        status = 'Poor'
    else:
        status = 'Critical'
    
    # Generate factors/feedback
    factors = []
    if moisture_status == 'poor':
        factors.append('Soil moisture is too ' + ('low' if moisture < 20 else 'high'))
    elif moisture_status == 'fair':
        factors.append('Soil moisture is suboptimal')
    
    if temp_status == 'poor':
        factors.append('Temperature is too ' + ('low' if temp < 55 else 'high'))
    elif temp_status == 'fair':
        factors.append('Temperature is outside optimal range')
    
    if light_status == 'poor':
        factors.append('Light levels are too ' + ('low' if light < 100 else 'high'))
    elif light_status == 'fair':
        factors.append('Light levels are suboptimal')
    
    if trend_score < 15:
        factors.append('Recent readings show declining conditions')
    
    if not factors:
        factors.append('All conditions are optimal')
    
    return {
        'score': round(total_score, 1),
        'status': status,
        'details': {
            'moisture_score': round(moisture_score, 1),
            'temperature_score': round(temp_score, 1),
            'light_score': round(light_score, 1),
            'trend_score': round(trend_score, 1)
        },
        'factors': factors,
        'current_values': {
            'moisture': round(moisture, 1),
            'temperature': round(temp, 1),
            'light': round(light, 1)
        }
    }

@app.route('/api/plant-health/<int:plant_id>', methods=['GET'])
@login_required_unless_demo
def get_plant_health(plant_id):
    """Get plant health score for a specific plant using ML model if available"""
    if DEMO_ENVIRONMENT:
        return jsonify(demo_generator.get_plant_health())

    plant = Plant.query.filter_by(id=plant_id, user_id=current_user.id).first()
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    
    # Try ML model first if available
    if health_classifier is not None:
        try:
            # Get recent sensor readings
            recent_readings = SensorReading.query.filter_by(plant_id=plant_id)\
                .order_by(SensorReading.timestamp.desc()).limit(5).all()
            
            # Format sensor readings for ML model (oldest first)
            sensor_readings = []
            for reading in reversed(recent_readings):
                sensor_readings.append({
                    'moisture': reading.moisture,
                    'temperature': reading.temperature,
                    'light': reading.light,
                    'timestamp': reading.timestamp
                })
            
            # Get current weather data (use user's location)
            weather_data = {}
            if current_user.latitude and current_user.longitude:
                try:
                    # Fetch weather from NWS API
                    grid_url = f'https://api.weather.gov/points/{current_user.latitude},{current_user.longitude}'
                    grid_response = requests.get(grid_url, headers=NWS_HEADERS, timeout=10)
                    
                    if grid_response.ok:
                        grid_data = grid_response.json()
                        forecast_url = grid_data['properties']['forecast']
                        forecast_response = requests.get(forecast_url, headers=NWS_HEADERS, timeout=10)
                        
                        if forecast_response.ok:
                            forecast_data = forecast_response.json()
                            periods = forecast_data.get('properties', {}).get('periods', [])
                            if periods:
                                current = periods[0]
                                weather_data = {
                                    'temperature': current.get('temperature', 72),
                                    'humidity': current.get('relativeHumidity', {}).get('value', 60),
                                    'precipitation': current.get('probabilityOfPrecipitation', {}).get('value', 0)
                                }
                except Exception as e:
                    print(f'Error fetching weather for health model: {e}')
                    # Use defaults
                    weather_data = {'temperature': 72, 'humidity': 60, 'precipitation': 0}
            else:
                # Use defaults if no location
                weather_data = {'temperature': 72, 'humidity': 60, 'precipitation': 0}
            
            # Prepare plant data (currently minimal, will expand when plant data is available)
            plant_data = {
                'age_days': (datetime.now() - plant.created_at).days if plant.created_at else 30,
                # TODO: Add more plant-specific data when available:
                # 'plant_type': plant.plant_type,
                # 'optimal_moisture_min': plant.optimal_moisture_min,
                # 'optimal_moisture_max': plant.optimal_moisture_max,
                # 'optimal_temp_min': plant.optimal_temp_min,
                # 'optimal_temp_max': plant.optimal_temp_max,
                # 'optimal_light_min': plant.optimal_light_min,
                # 'optimal_light_max': plant.optimal_light_max,
                # 'watering_frequency_days': plant.watering_frequency_days,
                # 'days_since_last_watering': plant.days_since_last_watering,
                # 'care_level': plant.care_level,
                # 'native_climate': plant.native_climate,
            }
            
            # Predict using ML model
            ml_result = health_classifier.predict({
                'sensor_readings': sensor_readings,
                'weather_data': weather_data,
                'plant_data': plant_data  # Pass plant data (will use defaults for missing fields)
            })
            
            # Get rule-based score for details
            rule_based = calculate_plant_health_score(plant_id)
            
            # Combine ML prediction with rule-based details
            return jsonify({
                'score': ml_result['score_estimate'],
                'status': ml_result['category'],
                'confidence': ml_result['confidence'],
                'probabilities': ml_result['probabilities'],
                'model_type': 'ML (Random Forest)' if health_classifier.is_trained else 'Rule-Based',
                'details': rule_based.get('details', {}),
                'factors': rule_based.get('factors', []),
                'current_values': rule_based.get('current_values', {})
            })
        except Exception as e:
            print(f'Error using ML health model: {e}')
            import traceback
            traceback.print_exc()
            # Fallback to rule-based
            health = calculate_plant_health_score(plant_id)
            health['model_type'] = 'Rule-Based (ML failed)'
            return jsonify(health)
    else:
        # Use rule-based calculation
        health = calculate_plant_health_score(plant_id)
        health['model_type'] = 'Rule-Based'
        return jsonify(health)

@app.route('/api/chat', methods=['POST'])
@login_required_unless_demo
def chat():
    """Chat endpoint using AutoGen with OpenAI"""
    try:
        data = request.json
        user_message = data.get('message', '')
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        api_key = os.environ.get('OPENAI_API_KEY')
        # Demo mode without an API key: answer from the same placeholder plant context
        if DEMO_ENVIRONMENT and (not api_key or api_key.startswith('your_')):
            return jsonify(demo_generator.get_chat_reply(user_message, context))
        
        # Import OpenAI (will be configured when API key is provided)
        try:
            import openai
            
            # Get API key from environment (user will set this later)
            if not api_key:
                # Return helpful message if API key not set
                return jsonify({
                    'error': 'OpenAI API key not configured',
                    'message': 'Please set the OPENAI_API_KEY environment variable. The chatbot will be available once configured.',
                    'instructions': 'Set your OpenAI API key: export OPENAI_API_KEY=your_key_here'
                }), 503
            
            # Configure OpenAI
            openai.api_key = api_key
            
            # Create AutoGen agents
            config_list = [{
                'model': 'gpt-4',
                'api_key': api_key
            }]
            
            # Prepare comprehensive context for the assistant
            sensor_data = context.get('sensorData', {})
            weather_data = context.get('weatherData', {})
            health_data = context.get('healthData', {})
            prediction_data = context.get('prediction', {})
            recent_history = context.get('recentHistory', [])
            trends = context.get('trends')
            last_reading_time = context.get('lastReadingTime')
            
            # Format last reading time
            last_reading_str = 'N/A'
            if last_reading_time:
                try:
                    from datetime import datetime
                    if isinstance(last_reading_time, str):
                        dt = datetime.fromisoformat(last_reading_time.replace('Z', '+00:00'))
                    else:
                        dt = last_reading_time
                    last_reading_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    last_reading_str = str(last_reading_time)
            
            # Build context info string
            context_info = f"""
Current Plant Information:
- Plant Name: {context.get('plantName', 'Unknown')}
- Health Score: {health_data.get('score', 'N/A')}/100
- Health Status: {health_data.get('status', 'Unknown')}
- Last Reading Time: {last_reading_str}
- Demo Mode: {'yes — placeholder data' if DEMO_ENVIRONMENT or sensor_data.get('is_demo') else 'no — live sensors'}

Current Sensor Readings:
- Soil Moisture: {sensor_data.get('moisture', 'N/A')}%
- Temperature: {sensor_data.get('temperature', 'N/A')}°F
- Light Level: {sensor_data.get('light', 'N/A')} lux
- Humidity: {sensor_data.get('humidity', weather_data.get('humidity', 'N/A'))}%

Current Weather:
- Temperature: {weather_data.get('temperature', 'N/A')}°F
- Humidity: {weather_data.get('humidity', 'N/A')}%
- Forecast: {weather_data.get('forecast', weather_data.get('description', 'N/A'))}
- Precipitation: {weather_data.get('precipitation', 'N/A')}%
- Wind Speed: {weather_data.get('windSpeed', weather_data.get('wind_speed', 'N/A'))} mph

Watering Prediction:
- Hours Until Watering: {prediction_data.get('hoursUntilWatering', 'N/A')}
- Watering Frequency: {prediction_data.get('wateringFrequencyDays', 'N/A')} days
- Recommendation: {prediction_data.get('recommendation', 'N/A')}
- Model Type: {prediction_data.get('modelType', 'N/A')}
"""
            
            # Add recent history trends if available
            if recent_history and len(recent_history) > 0:
                context_info += f"""
Recent Sensor History (Last {len(recent_history)} readings):
"""
                for i, reading in enumerate(recent_history[-5:], 1):
                    reading_time = reading.get('timestamp', '')
                    if isinstance(reading_time, str):
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(reading_time.replace('Z', '+00:00'))
                            reading_time = dt.strftime('%H:%M:%S')
                        except:
                            pass
                    context_info += f"- Reading {i} ({reading_time}): Moisture={reading.get('moisture', 'N/A')}%, Temp={reading.get('temperature', 'N/A')}°F, Light={reading.get('light', 'N/A')} lux\n"
            
            # Add trends if available
            if trends:
                context_info += f"""
Sensor Trends (over recent readings):
- Moisture Change: {trends.get('moistureTrend', 0):+.1f}%
- Temperature Change: {trends.get('temperatureTrend', 0):+.1f}°F
- Light Change: {trends.get('lightTrend', 0):+.1f} lux
"""
            
            # Add health breakdown if available (supports details or breakdown keys)
            health_details = None
            if health_data and isinstance(health_data, dict):
                health_details = health_data.get('details') or health_data.get('breakdown')
            if health_details:
                context_info += f"""
Health Score Breakdown:
- Moisture Score: {health_details.get('moisture_score', 'N/A')}
- Temperature Score: {health_details.get('temperature_score', 'N/A')}
- Light Score: {health_details.get('light_score', 'N/A')}
- Trend Score: {health_details.get('trend_score', health_details.get('consistency_score', 'N/A'))}
"""
            
            # Use OpenAI directly with AutoGen wrapper for better compatibility
            from openai import OpenAI
            
            client = OpenAI(api_key=api_key)
            
            demo_note = ""
            if DEMO_ENVIRONMENT or sensor_data.get('is_demo'):
                demo_note = (
                    "\nNOTE: This session is DEMO_ENVIRONMENT. Sensor/weather/health numbers are "
                    "placeholders for a basil plant demo. Still answer as if advising on this plant, "
                    "and briefly mention that readings are demo placeholders when relevant.\n"
                )

            # Create system message with context
            system_message = f"""You are a helpful plant care assistant. You help users understand their plant's health, 
provide care recommendations, and answer questions about plant maintenance. Use the following REAL-TIME context 
to provide personalized advice:

{context_info}
{demo_note}
IMPORTANT GUIDELINES:
- Use the sensor readings, health score, weather, and watering prediction above — stay synced with those numbers
- Use the recent history and trends to identify patterns and changes
- Reference specific sensor readings and timestamps when relevant
- Consider the watering prediction when giving watering advice
- Be specific about what the data indicates and what actions to take
- If trends show declining moisture or other concerning patterns, mention them
- Reference the health score breakdown to explain which factors are affecting plant health

Be friendly, informative, and provide actionable advice based on the current sensor readings, trends, and health data."""
            
            # Call OpenAI API - try multiple models in order of preference
            models_to_try = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            completion = None
            model_used = None
            
            for model_name in models_to_try:
                try:
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0.7
                    )
                    model_used = model_name
                    break
                except Exception as e:
                    error_str = str(e)
                    # If model not found, try next model
                    if 'model_not_found' in error_str or 'does not exist' in error_str:
                        continue
                    # For other errors (quota, rate limit, etc.), raise immediately
                    raise
            
            if not completion:
                return jsonify({
                    'error': 'No available models',
                    'message': 'None of the OpenAI models (gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo) are available for your account. Please check your OpenAI account access.',
                    'instructions': 'Visit https://platform.openai.com/ to check your account status and available models.'
                }), 503
            
            # Extract response
            message_content = completion.choices[0].message.content
            
            return jsonify({
                'message': message_content,
                'timestamp': datetime.now().isoformat(),
                'model': model_used,
                'is_demo': DEMO_ENVIRONMENT,
            })
            
        except ImportError:
            # Fallback if AutoGen not installed
            if DEMO_ENVIRONMENT:
                return jsonify(demo_generator.get_chat_reply(user_message, context))
            return jsonify({
                'error': 'AutoGen not installed',
                'message': 'Please install AutoGen: pip install pyautogen openai'
            }), 503
            
    except Exception as e:
        error_str = str(e)
        print(f'Chat error: {e}')
        import traceback
        traceback.print_exc()

        # In demo mode, never hard-fail the chat UI — answer from placeholder context
        if DEMO_ENVIRONMENT:
            try:
                return jsonify(demo_generator.get_chat_reply(
                    request.json.get('message', '') if request.json else '',
                    request.json.get('context', {}) if request.json else {}
                ))
            except Exception:
                pass
        
        # Provide helpful error messages for common issues
        if 'insufficient_quota' in error_str or 'quota' in error_str.lower():
            return jsonify({
                'error': 'OpenAI quota exceeded',
                'message': 'Your OpenAI account has exceeded its quota. Please add credits to your account.',
                'instructions': 'Visit https://platform.openai.com/account/billing to add credits or upgrade your plan.'
            }), 503
        elif 'rate_limit' in error_str.lower():
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests to OpenAI API. Please wait a moment and try again.',
                'instructions': 'The chatbot will be available again shortly.'
            }), 429
        elif 'model_not_found' in error_str or 'does not exist' in error_str:
            return jsonify({
                'error': 'Model not available',
                'message': 'The requested OpenAI model is not available for your account.',
                'instructions': 'Please check your OpenAI account tier and available models at https://platform.openai.com/'
            }), 503
        else:
            return jsonify({
                'error': str(e),
                'message': 'Sorry, I encountered an error. Please try again.'
            }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Initialize database
def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
