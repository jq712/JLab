from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from utils import db
import enum

# Create blueprint
categories_bp = Blueprint('categories', __name__)

# Category types enum
class CategoryType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

# Input validation schemas
class CategorySchema(Schema):
    name = fields.String(required=True)
    type = fields.String(required=True, validate=validate.OneOf([t.value for t in CategoryType]))
    icon = fields.String()
    color = fields.String(validate=validate.Regexp(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'))

# Route definitions
@categories_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_categories():
    """Get all categories for the current user"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Build query based on optional type filter
    category_type = request.args.get('type')
    if category_type and category_type in [t.value for t in CategoryType]:
        query = "SELECT * FROM categories WHERE user_id = %s AND type = %s ORDER BY name"
        categories = db.fetch_all(conn, query, (current_user_id, category_type))
    else:
        query = "SELECT * FROM categories WHERE user_id = %s ORDER BY name"
        categories = db.fetch_all(conn, query, (current_user_id,))
    
    return jsonify({"categories": categories}), 200

@categories_bp.route('/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """Get a specific category by ID"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    query = "SELECT * FROM categories WHERE id = %s AND user_id = %s"
    category = db.fetch_one(conn, query, (category_id, current_user_id))
    
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    return jsonify({"category": category}), 200

@categories_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    """Create a new transaction category"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Validate input data
    schema = CategorySchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Validate category type
    try:
        CategoryType(data['type'])
    except ValueError:
        return jsonify({"message": "Invalid category type"}), 400
    
    # Check if category with same name and type already exists
    check_query = "SELECT id FROM categories WHERE name = %s AND type = %s AND user_id = %s"
    existing = db.fetch_one(conn, check_query, (data['name'], data['type'], current_user_id))
    
    if existing:
        return jsonify({"message": "Category with this name and type already exists"}), 409
    
    # Create new category
    try:
        query = """
            INSERT INTO categories (name, type, icon, color, user_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data['name'],
            data['type'],
            data.get('icon'),
            data.get('color'),
            current_user_id
        )
        db.execute_with_commit(conn, query, params)
        
        # Get the newly created category
        query = "SELECT * FROM categories WHERE user_id = %s ORDER BY id DESC LIMIT 1"
        category = db.fetch_one(conn, query, (current_user_id,))
        
        return jsonify({
            "message": "Category created successfully",
            "category": category
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create category", "error": str(e)}), 500

@categories_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """Update an existing category"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Check if category exists and belongs to user
    check_query = "SELECT * FROM categories WHERE id = %s AND user_id = %s"
    category = db.fetch_one(conn, check_query, (category_id, current_user_id))
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    # Validate input data
    schema = CategorySchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Validate category type if provided
    if 'type' in data:
        try:
            CategoryType(data['type'])
        except ValueError:
            return jsonify({"message": "Invalid category type"}), 400
    
    # Check for duplicate after update
    if 'name' in data or 'type' in data:
        check_query = """
            SELECT id FROM categories 
            WHERE name = %s AND type = %s AND user_id = %s AND id != %s
        """
        params = (
            data.get('name', category['name']),
            data.get('type', category['type']),
            current_user_id,
            category_id
        )
        existing = db.fetch_one(conn, check_query, params)
        
        if existing:
            return jsonify({"message": "Category with this name and type already exists"}), 409
    
    # Build update query dynamically based on provided fields
    update_fields = []
    params = []
    for field in ['name', 'type', 'icon', 'color']:
        if field in data:
            update_fields.append(f"{field} = %s")
            params.append(data[field])
    
    if not update_fields:
        return jsonify({"message": "No fields to update"}), 400
    
    # Add category_id and user_id to params
    params.extend([category_id, current_user_id])
    
    # Update category
    query = f"""
        UPDATE categories 
        SET {', '.join(update_fields)}
        WHERE id = %s AND user_id = %s
    """
    db.execute_with_commit(conn, query, params)
    
    # Get updated category
    query = "SELECT * FROM categories WHERE id = %s"
    updated_category = db.fetch_one(conn, query, (category_id,))
    
    return jsonify({
        "message": "Category updated successfully",
        "category": updated_category
    }), 200

@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category"""
    current_user_id = get_jwt_identity()
    conn = g.db
    
    # Check if category exists and belongs to user
    check_query = "SELECT id FROM categories WHERE id = %s AND user_id = %s"
    category = db.fetch_one(conn, check_query, (category_id, current_user_id))
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    # Check if category is in use by any transactions
    check_query = "SELECT COUNT(*) as count FROM transactions WHERE category_id = %s"
    result = db.fetch_one(conn, check_query, (category_id,))
    if result and result['count'] > 0:
        return jsonify({
            "message": "Cannot delete category because it is assigned to transactions",
            "transaction_count": result['count']
        }), 400
    
    # Delete category
    try:
        query = "DELETE FROM categories WHERE id = %s AND user_id = %s"
        db.execute_with_commit(conn, query, (category_id, current_user_id))
        return jsonify({"message": "Category deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to delete category", "error": str(e)}), 500 