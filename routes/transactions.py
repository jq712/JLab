from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime, date
from enum import Enum

# Create blueprint
transactions_bp = Blueprint('transactions', __name__)

class CategoryType(Enum):
    INCOME = 'income'
    EXPENSE = 'expense'

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
def build_transaction_filters(filters, user_id):
    """Build SQL WHERE clause for transaction filters"""
    conditions = ["user_id = %s"]
    params = [user_id]
    
    if 'start_date' in filters:
        conditions.append("date >= %s")
        params.append(filters['start_date'])
    if 'end_date' in filters:
        conditions.append("date <= %s")
        params.append(filters['end_date'])
    if 'account_id' in filters:
        conditions.append("account_id = %s")
        params.append(filters['account_id'])
    if 'category_id' in filters:
        conditions.append("category_id = %s")
        params.append(filters['category_id'])
    if 'min_amount' in filters:
        conditions.append("amount >= %s")
        params.append(filters['min_amount'])
    if 'max_amount' in filters:
        conditions.append("amount <= %s")
        params.append(filters['max_amount'])
    if 'description' in filters:
        conditions.append("description ILIKE %s")
        params.append(f"%{filters['description']}%")
    if 'is_reconciled' in filters:
        conditions.append("is_reconciled = %s")
        params.append(filters['is_reconciled'])
    if 'category_type' in filters:
        conditions.append("categories.type = %s")
        params.append(filters['category_type'])
    
    return " AND ".join(conditions), params

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
    where_clause, params = build_transaction_filters(filter_params, current_user_id)
    
    # Add sorting
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    sort_column = {
        'date': 'transactions.date',
        'amount': 'transactions.amount',
        'description': 'transactions.description'
    }.get(sort_by, 'transactions.date')
    
    query = f"""
        SELECT t.*, c.type as category_type, a.name as account_name, c.name as category_name
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN categories c ON t.category_id = c.id
        WHERE {where_clause}
        ORDER BY {sort_column} {sort_order}
    """
    
    transactions = g.db.fetch_all(query, params)
    
    return jsonify({
        "transactions": transactions,
        "count": len(transactions)
    }), 200

@transactions_bp.route('/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    """Get a specific transaction by ID"""
    current_user_id = get_jwt_identity()
    
    query = """
        SELECT t.*, c.type as category_type, a.name as account_name, c.name as category_name
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN categories c ON t.category_id = c.id
        WHERE t.id = %s AND t.user_id = %s
    """
    transaction = g.db.fetch_one(query, [transaction_id, current_user_id])
    
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    
    return jsonify({"transaction": transaction}), 200

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
    account_query = "SELECT id FROM accounts WHERE id = %s AND user_id = %s"
    account = g.db.fetch_one(account_query, [data['account_id'], current_user_id])
    if not account:
        return jsonify({"message": "Account not found or does not belong to you"}), 404
    
    # Verify category exists and belongs to user
    category_query = "SELECT id FROM categories WHERE id = %s AND user_id = %s"
    category = g.db.fetch_one(category_query, [data['category_id'], current_user_id])
    if not category:
        return jsonify({"message": "Category not found or does not belong to you"}), 404
    
    # Create new transaction
    try:
        insert_query = """
            INSERT INTO transactions 
            (date, description, amount, account_id, category_id, user_id, notes, is_reconciled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = [
            data['date'],
            data['description'],
            data['amount'],
            data['account_id'],
            data['category_id'],
            current_user_id,
            data.get('notes'),
            data.get('is_reconciled', False)
        ]
        
        # Start transaction
        g.db.begin()
        
        # Insert transaction
        result = g.db.fetch_one(insert_query, params)
        transaction_id = result['id']
        
        # Update account balance
        update_balance_query = """
            UPDATE accounts 
            SET balance = balance + %s 
            WHERE id = %s
        """
        g.db.execute(update_balance_query, [data['amount'], data['account_id']])
        
        # Commit transaction
        g.db.commit()
        
        # Fetch the created transaction
        fetch_query = """
            SELECT t.*, c.type as category_type, a.name as account_name, c.name as category_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN categories c ON t.category_id = c.id
            WHERE t.id = %s
        """
        transaction = g.db.fetch_one(fetch_query, [transaction_id])
        
        return jsonify({
            "message": "Transaction created successfully",
            "transaction": transaction
        }), 201
        
    except Exception as e:
        g.db.rollback()
        return jsonify({"message": "Failed to create transaction", "error": str(e)}), 500

@transactions_bp.route('/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    """Update an existing transaction"""
    current_user_id = get_jwt_identity()
    
    # Check if transaction exists and belongs to user
    fetch_query = """
        SELECT * FROM transactions 
        WHERE id = %s AND user_id = %s
    """
    transaction = g.db.fetch_one(fetch_query, [transaction_id, current_user_id])
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
        account_query = "SELECT id FROM accounts WHERE id = %s AND user_id = %s"
        account = g.db.fetch_one(account_query, [data['account_id'], current_user_id])
        if not account:
            return jsonify({"message": "Account not found or does not belong to you"}), 404
    
    # Check category if provided
    if 'category_id' in data:
        category_query = "SELECT id FROM categories WHERE id = %s AND user_id = %s"
        category = g.db.fetch_one(category_query, [data['category_id'], current_user_id])
        if not category:
            return jsonify({"message": "Category not found or does not belong to you"}), 404
    
    try:
        g.db.begin()
        
        # If amount is changing, update account balances
        if 'amount' in data:
            old_amount = transaction['amount']
            new_amount = data['amount']
            amount_diff = new_amount - old_amount
            
            # Update old account balance
            update_old_balance_query = """
                UPDATE accounts 
                SET balance = balance - %s 
                WHERE id = %s
            """
            g.db.execute(update_old_balance_query, [old_amount, transaction['account_id']])
            
            # Update new account balance if account is changing
            target_account_id = data.get('account_id', transaction['account_id'])
            update_new_balance_query = """
                UPDATE accounts 
                SET balance = balance + %s 
                WHERE id = %s
            """
            g.db.execute(update_new_balance_query, [new_amount, target_account_id])
        
        # Build update query
        update_fields = []
        update_params = []
        for field in ['date', 'description', 'amount', 'account_id', 'category_id', 'notes', 'is_reconciled']:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_params.append(data[field])
        
        if update_fields:
            update_query = f"""
                UPDATE transactions 
                SET {', '.join(update_fields)}
                WHERE id = %s AND user_id = %s
            """
            update_params.extend([transaction_id, current_user_id])
            g.db.execute(update_query, update_params)
        
        g.db.commit()
        
        # Fetch updated transaction
        fetch_updated_query = """
            SELECT t.*, c.type as category_type, a.name as account_name, c.name as category_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN categories c ON t.category_id = c.id
            WHERE t.id = %s
        """
        updated_transaction = g.db.fetch_one(fetch_updated_query, [transaction_id])
        
        return jsonify({
            "message": "Transaction updated successfully",
            "transaction": updated_transaction
        }), 200
        
    except Exception as e:
        g.db.rollback()
        return jsonify({"message": "Failed to update transaction", "error": str(e)}), 500

@transactions_bp.route('/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """Delete a transaction"""
    current_user_id = get_jwt_identity()
    
    # Check if transaction exists and belongs to user
    fetch_query = """
        SELECT * FROM transactions 
        WHERE id = %s AND user_id = %s
    """
    transaction = g.db.fetch_one(fetch_query, [transaction_id, current_user_id])
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    
    try:
        g.db.begin()
        
        # Update account balance
        update_balance_query = """
            UPDATE accounts 
            SET balance = balance - %s 
            WHERE id = %s
        """
        g.db.execute(update_balance_query, [transaction['amount'], transaction['account_id']])
        
        # Delete transaction
        delete_query = """
            DELETE FROM transactions 
            WHERE id = %s AND user_id = %s
        """
        g.db.execute(delete_query, [transaction_id, current_user_id])
        
        g.db.commit()
        return jsonify({"message": "Transaction deleted successfully"}), 200
        
    except Exception as e:
        g.db.rollback()
        return jsonify({"message": "Failed to delete transaction", "error": str(e)}), 500 