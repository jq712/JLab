from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema, fields, validate, ValidationError
from email_validator import validate_email, EmailNotValidError
from utils import db

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Input validation schemas
class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)

# Route definitions
@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    # Validate input data
    schema = RegisterSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    conn = g.db
    
    # Check if email already exists
    check_query = "SELECT id FROM users WHERE email = %s"
    existing_user = db.fetch_one(conn, check_query, (data['email'],))
    if existing_user:
        return jsonify({"message": "Email already registered"}), 409
    
    # Create new user
    try:
        insert_query = """
            INSERT INTO users (email, password_hash, first_name, last_name, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data['email'],
            generate_password_hash(data['password']),
            data['first_name'],
            data['last_name'],
            True
        )
        db.execute_with_commit(conn, insert_query, params)
        
        # Get the newly created user
        user_query = "SELECT * FROM users WHERE email = %s"
        user = db.fetch_one(conn, user_query, (data['email'],))
        
        # Generate tokens
        access_token = create_access_token(identity=user['id'])
        refresh_token = create_refresh_token(identity=user['id'])
        
        # Remove password hash from response
        user.pop('password_hash', None)
        
        return jsonify({
            "message": "User registered successfully",
            "user": user,
            "tokens": {
                "access": access_token,
                "refresh": refresh_token
            }
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Registration failed", "error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login an existing user"""
    # Validate input data
    schema = LoginSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    conn = g.db
    
    # Get user by email
    query = "SELECT * FROM users WHERE email = %s"
    user = db.fetch_one(conn, query, (data['email'],))
    
    # Check user and password
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({"message": "Invalid email or password"}), 401
    
    # Check if user is active
    if not user['is_active']:
        return jsonify({"message": "Account is disabled"}), 403
        
    # Generate tokens
    access_token = create_access_token(identity=user['id'])
    refresh_token = create_refresh_token(identity=user['id'])
    
    # Remove password hash from response
    user.pop('password_hash', None)
    
    return jsonify({
        "message": "Login successful",
        "user": user,
        "tokens": {
            "access": access_token,
            "refresh": refresh_token
        }
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Verify user exists and is active
    query = "SELECT id, is_active FROM users WHERE id = %s"
    user = db.fetch_one(conn, query, (current_user_id,))
    
    if not user or not user['is_active']:
        return jsonify({"message": "User not found or inactive"}), 401
    
    # Generate new access token
    access_token = create_access_token(identity=current_user_id)
    
    return jsonify({
        "message": "Token refreshed",
        "access_token": access_token
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current logged in user information"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    query = """
        SELECT id, email, first_name, last_name, is_active, created_at, updated_at 
        FROM users WHERE id = %s
    """
    user = db.fetch_one(conn, query, (current_user_id,))
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    return jsonify({"user": user}), 200 