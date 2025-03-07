import os
from flask import Flask, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import get_config
from utils import db
from routes import register_routes


def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = db.get_connection(current_app.config)
    return g.db


def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def create_app(config_name='development'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(get_config())
    
    # Enable CORS
    CORS(app)
    
    # Initialize JWT
    jwt = JWTManager(app)
    
    # Register database connection handlers
    app.teardown_appcontext(close_db)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register API routes
    register_routes(app)
    
    # Health check route
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy', 'message': 'Finance API is running'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True) 