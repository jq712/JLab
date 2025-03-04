from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from models.user import User
from marshmallow import Schema, fields, validate, ValidationError
from email_validator import validate_email, EmailNotValidError

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
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already registered"}), 409
    
    # Create new user
    try:
        user = User(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        user.save()
        
        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            "message": "User registered successfully",
            "user": user.to_dict(),
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
    
    # Check user and password
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"message": "Invalid email or password"}), 401
    
    # Check if user is active
    if not user.is_active:
        return jsonify({"message": "Account is disabled"}), 403
        
    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
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
    
    # Verify user exists and is active
    user = User.query.get(current_user_id)
    if not user or not user.is_active:
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
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200 