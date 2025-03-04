from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.transaction import Transaction
from models.account import Account
from models.category import Category, CategoryType
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime, date

# Create blueprint
transactions_bp = Blueprint('transactions', __name__)

# Input validation schemas
class TransactionSchema(Schema):
    date = fields.Date(required=True)
    description = fields.String(required=True)
    amount = fields.Float(required=True)
    account_id = fields.Integer(required=True)
    category_id = fields.Integer(required=True)
    notes = fields.String()
    is_reconciled = fields.Boolean()

class TransactionFilterParams(Schema):
    start_date = fields.Date()
    end_date = fields.Date()
    account_id = fields.Integer()
    category_id = fields.Integer()
    min_amount = fields.Float()
    max_amount = fields.Float()
    description = fields.String()
    is_reconciled = fields.Boolean()
    category_type = fields.String(validate=validate.OneOf([t.value for t in CategoryType]))

# Helper functions
def apply_transaction_filters(query, filters, user_id):
    """Apply filters to transaction query"""
    if 'start_date' in filters:
        query = query.filter(Transaction.date >= filters['start_date'])
    if 'end_date' in filters:
        query = query.filter(Transaction.date <= filters['end_date'])
    if 'account_id' in filters:
        query = query.filter(Transaction.account_id == filters['account_id'])
    if 'category_id' in filters:
        query = query.filter(Transaction.category_id == filters['category_id'])
    if 'min_amount' in filters:
        query = query.filter(Transaction.amount >= filters['min_amount'])
    if 'max_amount' in filters:
        query = query.filter(Transaction.amount <= filters['max_amount'])
    if 'description' in filters:
        query = query.filter(Transaction.description.ilike(f'%{filters["description"]}%'))
    if 'is_reconciled' in filters:
        query = query.filter(Transaction.is_reconciled == filters['is_reconciled'])
    if 'category_type' in filters:
        category_type = CategoryType(filters['category_type'])
        # Join with the Category model to filter by category type
        query = query.join(Category, Transaction.category_id == Category.id) \
                      .filter(Category.type == category_type)
    
    # Always filter by user_id for security
    query = query.filter(Transaction.user_id == user_id)
    
    return query

# Route definitions
@transactions_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_transactions():
    """Get all transactions for the current user with optional filtering"""
    current_user_id = get_jwt_identity()
    
    # Parse filter parameters
    filter_schema = TransactionFilterParams()
    filter_params = {}
    for key, value in request.args.items():
        if key in filter_schema.fields:
            if key in ['start_date', 'end_date']:
                try:
                    filter_params[key] = datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    pass
            elif key in ['account_id', 'category_id']:
                try:
                    filter_params[key] = int(value)
                except ValueError:
                    pass
            elif key in ['min_amount', 'max_amount']:
                try:
                    filter_params[key] = float(value)
                except ValueError:
                    pass
            elif key == 'is_reconciled':
                filter_params[key] = value.lower() in ['true', '1', 'yes']
            else:
                filter_params[key] = value
    
    # Build query with filters
    query = Transaction.query
    query = apply_transaction_filters(query, filter_params, current_user_id)
    
    # Add sorting - default to newest transactions first
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_by == 'date':
        query = query.order_by(Transaction.date.desc() if sort_order.lower() == 'desc' else Transaction.date)
    elif sort_by == 'amount':
        query = query.order_by(Transaction.amount.desc() if sort_order.lower() == 'desc' else Transaction.amount)
    elif sort_by == 'description':
        query = query.order_by(Transaction.description.desc() if sort_order.lower() == 'desc' else Transaction.description)
    
    # Execute query
    transactions = query.all()
    
    return jsonify({
        "transactions": [transaction.to_dict() for transaction in transactions],
        "count": len(transactions)
    }), 200

@transactions_bp.route('/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    """Get a specific transaction by ID"""
    current_user_id = get_jwt_identity()
    
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user_id).first()
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    
    return jsonify({"transaction": transaction.to_dict()}), 200

@transactions_bp.route('/', methods=['POST'])
@jwt_required()
def create_transaction():
    """Create a new transaction"""
    current_user_id = get_jwt_identity()
    
    # Validate input data
    schema = TransactionSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Verify account exists and belongs to user
    account = Account.query.filter_by(id=data['account_id'], user_id=current_user_id).first()
    if not account:
        return jsonify({"message": "Account not found or does not belong to you"}), 404
    
    # Verify category exists and belongs to user
    category = Category.query.filter_by(id=data['category_id'], user_id=current_user_id).first()
    if not category:
        return jsonify({"message": "Category not found or does not belong to you"}), 404
    
    # Create new transaction
    try:
        transaction = Transaction(
            date=data['date'],
            description=data['description'],
            amount=data['amount'],
            account_id=data['account_id'],
            category_id=data['category_id'],
            user_id=current_user_id,
            notes=data.get('notes'),
            is_reconciled=data.get('is_reconciled', False)
        )
        
        # Use custom save method to update account balance
        transaction.save()
        
        return jsonify({
            "message": "Transaction created successfully",
            "transaction": transaction.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create transaction", "error": str(e)}), 500

@transactions_bp.route('/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    """Update an existing transaction"""
    current_user_id = get_jwt_identity()
    
    # Check if transaction exists and belongs to user
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user_id).first()
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    
    # Validate input data
    schema = TransactionSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Check account if provided
    if 'account_id' in data:
        account = Account.query.filter_by(id=data['account_id'], user_id=current_user_id).first()
        if not account:
            return jsonify({"message": "Account not found or does not belong to you"}), 404
        transaction.account_id = data['account_id']
    
    # Check category if provided
    if 'category_id' in data:
        category = Category.query.filter_by(id=data['category_id'], user_id=current_user_id).first()
        if not category:
            return jsonify({"message": "Category not found or does not belong to you"}), 404
        transaction.category_id = data['category_id']
    
    # Update other fields
    if 'date' in data:
        transaction.date = data['date']
    if 'description' in data:
        transaction.description = data['description']
    if 'amount' in data:
        # Use special method to update amount and account balance
        transaction.update_amount(data['amount'])
    if 'notes' in data:
        transaction.notes = data['notes']
    if 'is_reconciled' in data:
        transaction.is_reconciled = data['is_reconciled']
    
    # Save changes (if amount wasn't updated)
    if 'amount' not in data:
        transaction.save()
    
    return jsonify({
        "message": "Transaction updated successfully",
        "transaction": transaction.to_dict()
    }), 200

@transactions_bp.route('/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """Delete a transaction"""
    current_user_id = get_jwt_identity()
    
    # Check if transaction exists and belongs to user
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user_id).first()
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    
    # Use custom delete method to update account balance
    try:
        transaction.delete()
        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to delete transaction", "error": str(e)}), 500 