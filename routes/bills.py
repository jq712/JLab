from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.bill import Bill, BillFrequency
from models.category import Category
from models.account import Account
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime, date, timedelta

# Create blueprint
bills_bp = Blueprint('bills', __name__)

# Input validation schemas
class BillSchema(Schema):
    name = fields.String(required=True)
    amount = fields.Float(required=True)
    due_date = fields.Date(required=True)
    frequency = fields.String(required=True, validate=validate.OneOf([f.value for f in BillFrequency]))
    category_id = fields.Integer(required=True)
    account_id = fields.Integer()
    is_paid = fields.Boolean()
    notes = fields.String()

# Route definitions
@bills_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_bills():
    """Get all bills for the current user"""
    current_user_id = get_jwt_identity()
    
    # Get filter parameters
    is_paid = request.args.get('is_paid')
    if is_paid is not None:
        is_paid = is_paid.lower() in ['true', '1', 'yes']
        bills = Bill.query.filter_by(user_id=current_user_id, is_paid=is_paid).all()
    else:
        bills = Bill.query.filter_by(user_id=current_user_id).all()
    
    # Get time range parameters for due dates
    days_range = request.args.get('days_range')
    if days_range:
        try:
            days = int(days_range)
            today = date.today()
            end_date = today + timedelta(days=days)
            bills = [bill for bill in bills if today <= bill.due_date <= end_date]
        except ValueError:
            pass
    
    return jsonify({
        "bills": [bill.to_dict() for bill in bills]
    }), 200

@bills_bp.route('/<int:bill_id>', methods=['GET'])
@jwt_required()
def get_bill(bill_id):
    """Get a specific bill by ID"""
    current_user_id = get_jwt_identity()
    
    bill = Bill.query.filter_by(id=bill_id, user_id=current_user_id).first()
    if not bill:
        return jsonify({"message": "Bill not found"}), 404
    
    return jsonify({"bill": bill.to_dict()}), 200

@bills_bp.route('/', methods=['POST'])
@jwt_required()
def create_bill():
    """Create a new bill"""
    current_user_id = get_jwt_identity()
    
    # Validate input data
    schema = BillSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Verify category exists and belongs to user
    category = Category.query.filter_by(id=data['category_id'], user_id=current_user_id).first()
    if not category:
        return jsonify({"message": "Category not found or does not belong to you"}), 404
    
    # Verify account exists and belongs to user (if provided)
    account = None
    if 'account_id' in data and data['account_id']:
        account = Account.query.filter_by(id=data['account_id'], user_id=current_user_id).first()
        if not account:
            return jsonify({"message": "Account not found or does not belong to you"}), 404
    
    # Map frequency string to enum
    try:
        frequency = BillFrequency(data['frequency'])
    except ValueError:
        return jsonify({"message": "Invalid bill frequency"}), 400
    
    # Create new bill
    try:
        bill = Bill(
            name=data['name'],
            amount=data['amount'],
            due_date=data['due_date'],
            frequency=frequency,
            category_id=data['category_id'],
            user_id=current_user_id,
            account_id=data.get('account_id'),
            is_paid=data.get('is_paid', False),
            notes=data.get('notes')
        )
        bill.save()
        
        return jsonify({
            "message": "Bill created successfully",
            "bill": bill.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create bill", "error": str(e)}), 500

@bills_bp.route('/<int:bill_id>', methods=['PUT'])
@jwt_required()
def update_bill(bill_id):
    """Update an existing bill"""
    current_user_id = get_jwt_identity()
    
    # Check if bill exists and belongs to user
    bill = Bill.query.filter_by(id=bill_id, user_id=current_user_id).first()
    if not bill:
        return jsonify({"message": "Bill not found"}), 404
    
    # Validate input data
    schema = BillSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Check category if provided
    if 'category_id' in data:
        category = Category.query.filter_by(id=data['category_id'], user_id=current_user_id).first()
        if not category:
            return jsonify({"message": "Category not found or does not belong to you"}), 404
        bill.category_id = data['category_id']
    
    # Check account if provided
    if 'account_id' in data:
        if data['account_id'] is None:
            bill.account_id = None
        else:
            account = Account.query.filter_by(id=data['account_id'], user_id=current_user_id).first()
            if not account:
                return jsonify({"message": "Account not found or does not belong to you"}), 404
            bill.account_id = data['account_id']
    
    # Update other fields
    if 'name' in data:
        bill.name = data['name']
    if 'amount' in data:
        bill.amount = data['amount']
    if 'due_date' in data:
        bill.due_date = data['due_date']
    if 'frequency' in data:
        try:
            bill.frequency = BillFrequency(data['frequency'])
        except ValueError:
            return jsonify({"message": "Invalid bill frequency"}), 400
    if 'is_paid' in data:
        bill.is_paid = data['is_paid']
    if 'notes' in data:
        bill.notes = data['notes']
    
    bill.save()
    
    return jsonify({
        "message": "Bill updated successfully",
        "bill": bill.to_dict()
    }), 200

@bills_bp.route('/<int:bill_id>/pay', methods=['POST'])
@jwt_required()
def mark_bill_as_paid(bill_id):
    """Mark a bill as paid"""
    current_user_id = get_jwt_identity()
    
    # Check if bill exists and belongs to user
    bill = Bill.query.filter_by(id=bill_id, user_id=current_user_id).first()
    if not bill:
        return jsonify({"message": "Bill not found"}), 404
    
    # Mark as paid
    bill.mark_as_paid()
    
    return jsonify({
        "message": "Bill marked as paid",
        "bill": bill.to_dict()
    }), 200

@bills_bp.route('/<int:bill_id>/unpay', methods=['POST'])
@jwt_required()
def mark_bill_as_unpaid(bill_id):
    """Mark a bill as unpaid"""
    current_user_id = get_jwt_identity()
    
    # Check if bill exists and belongs to user
    bill = Bill.query.filter_by(id=bill_id, user_id=current_user_id).first()
    if not bill:
        return jsonify({"message": "Bill not found"}), 404
    
    # Mark as unpaid
    bill.mark_as_unpaid()
    
    return jsonify({
        "message": "Bill marked as unpaid",
        "bill": bill.to_dict()
    }), 200

@bills_bp.route('/<int:bill_id>', methods=['DELETE'])
@jwt_required()
def delete_bill(bill_id):
    """Delete a bill"""
    current_user_id = get_jwt_identity()
    
    # Check if bill exists and belongs to user
    bill = Bill.query.filter_by(id=bill_id, user_id=current_user_id).first()
    if not bill:
        return jsonify({"message": "Bill not found"}), 404
    
    # Delete bill
    try:
        bill.delete()
        return jsonify({"message": "Bill deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to delete bill", "error": str(e)}), 500 