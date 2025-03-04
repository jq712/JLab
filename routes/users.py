from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from marshmallow import Schema, fields, validate, ValidationError

# Create blueprint
users_bp = Blueprint('users', __name__)

# Input validation schemas
class UpdateProfileSchema(Schema):
    first_name = fields.String()
    last_name = fields.String()

class ChangePasswordSchema(Schema):
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8))
    confirm_password = fields.String(required=True)

# Route definitions
@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user's profile information"""
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user's profile information"""
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Validate input data
    schema = UpdateProfileSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Update user information
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    
    user.save()
    
    return jsonify({
        "message": "Profile updated successfully",
        "user": user.to_dict()
    }), 200

@users_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user's password"""
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Validate input data
    schema = ChangePasswordSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Verify current password
    if not user.check_password(data['current_password']):
        return jsonify({"message": "Current password is incorrect"}), 401
    
    # Check if new password and confirmation match
    if data['new_password'] != data['confirm_password']:
        return jsonify({"message": "New password and confirmation do not match"}), 400
    
    # Update password
    user.update_password(data['new_password'])
    
    return jsonify({"message": "Password changed successfully"}), 200

@users_bp.route('/deactivate', methods=['POST'])
@jwt_required()
def deactivate_account():
    """Deactivate user's account"""
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Deactivate account
    user.is_active = False
    user.save()
    
    return jsonify({"message": "Account deactivated successfully"}), 200 