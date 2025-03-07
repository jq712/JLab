from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from utils import db
import enum

# Create blueprint
accounts_bp = Blueprint('accounts', __name__)

# Account types enum
class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

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
    conn = g.db
    
    query = """
        SELECT * FROM accounts 
        WHERE user_id = %s AND is_active = 1
        ORDER BY name
    """
    accounts = db.fetch_all(conn, query, (current_user_id,))
    
    return jsonify({"accounts": accounts}), 200

@accounts_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_account(account_id):
    """Get a specific account by ID"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    query = "SELECT * FROM accounts WHERE id = %s AND user_id = %s"
    account = db.fetch_one(conn, query, (account_id, current_user_id))
    
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    return jsonify({"account": account}), 200

@accounts_bp.route('/', methods=['POST'])
@jwt_required()
def create_account():
    """Create a new financial account"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Validate input data
    schema = AccountSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Map string account type to enum to validate
    try:
        AccountType(data['account_type'])
    except ValueError:
        return jsonify({"message": "Invalid account type"}), 400
    
    # Create new account
    try:
        query = """
            INSERT INTO accounts (
                name, type, balance, currency, description, 
                institution, is_active, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['name'],
            data['account_type'],
            data.get('balance', 0.0),
            data.get('currency', 'USD'),
            data.get('description'),
            data.get('institution'),
            True,
            current_user_id
        )
        db.execute_with_commit(conn, query, params)
        
        # Get the newly created account
        query = "SELECT * FROM accounts WHERE user_id = %s ORDER BY id DESC LIMIT 1"
        account = db.fetch_one(conn, query, (current_user_id,))
        
        return jsonify({
            "message": "Account created successfully",
            "account": account
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create account", "error": str(e)}), 500

@accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_account(account_id):
    """Update an existing account"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Check if account exists and belongs to user
    check_query = "SELECT id FROM accounts WHERE id = %s AND user_id = %s"
    account = db.fetch_one(conn, check_query, (account_id, current_user_id))
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    # Validate input data
    schema = AccountSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Validate account type if provided
    if 'account_type' in data:
        try:
            AccountType(data['account_type'])
        except ValueError:
            return jsonify({"message": "Invalid account type"}), 400
    
    # Build update query dynamically based on provided fields
    update_fields = []
    params = []
    for field in ['name', 'account_type', 'currency', 'description', 'institution']:
        if field in data:
            update_fields.append(f"{field if field != 'account_type' else 'type'} = %s")
            params.append(data[field])
    
    if not update_fields:
        return jsonify({"message": "No fields to update"}), 400
    
    # Add account_id and user_id to params
    params.extend([account_id, current_user_id])
    
    # Update account
    query = f"""
        UPDATE accounts 
        SET {', '.join(update_fields)}
        WHERE id = %s AND user_id = %s
    """
    db.execute_with_commit(conn, query, params)
    
    # Get updated account
    query = "SELECT * FROM accounts WHERE id = %s"
    updated_account = db.fetch_one(conn, query, (account_id,))
    
    return jsonify({
        "message": "Account updated successfully",
        "account": updated_account
    }), 200

@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_account(account_id):
    """Soft delete an account (mark as inactive)"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Check if account exists and belongs to user
    check_query = "SELECT id FROM accounts WHERE id = %s AND user_id = %s"
    account = db.fetch_one(conn, check_query, (account_id, current_user_id))
    if not account:
        return jsonify({"message": "Account not found"}), 404
    
    # Soft delete (mark as inactive)
    query = "UPDATE accounts SET is_active = 0 WHERE id = %s AND user_id = %s"
    db.execute_with_commit(conn, query, (account_id, current_user_id))
    
    return jsonify({"message": "Account deleted successfully"}), 200 