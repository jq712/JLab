from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.account import Account, AccountType
from marshmallow import Schema, fields, validate, ValidationError
import enum

# Create blueprint
accounts_bp = Blueprint('accounts', __name__)

# Input validation schemas
class AccountSchema(Schema):
    name = fields.String(required=True)
    account_type = fields.String(required=True, validate=validate.OneOf([t.value for t in AccountType]))
    balance = fields.Float()
    currency = fields.String(validate=validate.Length(equal=3))
    description = fields.String()
    institution = fields.String()

# Route definitions
@accounts_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_accounts():
    """Get all accounts for the current user"""
    current_user_id = get_jwt_identity()
    
    accounts = Account.query.filter_by(user_id=current_user_id, is_active=1).all()
    
    return jsonify({
        "accounts": [account.to_dict() for account in accounts]
    }), 200

@accounts_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_account(account_id):
    """Get a specific account by ID"""
    current_user_id = get_jwt_identity()
    
    account = Account.query.filter_by(id=account_id, user_id=current_user_id).first()
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    return jsonify({"account": account.to_dict()}), 200

@accounts_bp.route('/', methods=['POST'])
@jwt_required()
def create_account():
    """Create a new financial account"""
    current_user_id = get_jwt_identity()
    
    # Validate input data
    schema = AccountSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Map string account type to enum
    try:
        account_type = AccountType(data['account_type'])
    except ValueError:
        return jsonify({"message": "Invalid account type"}), 400
    
    # Create new account
    try:
        account = Account(
            name=data['name'],
            account_type=account_type,
            user_id=current_user_id,
            balance=data.get('balance', 0.0),
            currency=data.get('currency', 'USD'),
            description=data.get('description'),
            institution=data.get('institution')
        )
        account.save()
        
        return jsonify({
            "message": "Account created successfully",
            "account": account.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create account", "error": str(e)}), 500

@accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_account(account_id):
    """Update an existing account"""
    current_user_id = get_jwt_identity()
    
    # Check if account exists and belongs to user
    account = Account.query.filter_by(id=account_id, user_id=current_user_id).first()
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    # Validate input data
    schema = AccountSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Update account fields
    if 'name' in data:
        account.name = data['name']
    if 'account_type' in data:
        try:
            account.account_type = AccountType(data['account_type'])
        except ValueError:
            return jsonify({"message": "Invalid account type"}), 400
    if 'currency' in data:
        account.currency = data['currency']
    if 'description' in data:
        account.description = data['description']
    if 'institution' in data:
        account.institution = data['institution']
    
    # Note: We intentionally don't allow direct balance update here
    # Balance should only be updated through transactions
    
    account.save()
    
    return jsonify({
        "message": "Account updated successfully",
        "account": account.to_dict()
    }), 200

@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_account(account_id):
    """Soft delete an account (mark as inactive)"""
    current_user_id = get_jwt_identity()
    
    # Check if account exists and belongs to user
    account = Account.query.filter_by(id=account_id, user_id=current_user_id).first()
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    # Soft delete (mark as inactive)
    account.is_active = 0
    account.save()
    
    return jsonify({"message": "Account deleted successfully"}), 200 