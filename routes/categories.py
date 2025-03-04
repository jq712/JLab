from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.category import Category, CategoryType
from marshmallow import Schema, fields, validate, ValidationError

# Create blueprint
categories_bp = Blueprint('categories', __name__)

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
    
    categories = Category.query.filter_by(user_id=current_user_id).all()
    
    # Optional type filter
    category_type = request.args.get('type')
    if category_type:
        try:
            category_type_enum = CategoryType(category_type)
            categories = [cat for cat in categories if cat.type == category_type_enum]
        except ValueError:
            # Invalid type parameter, return all categories
            pass
    
    return jsonify({
        "categories": [category.to_dict() for category in categories]
    }), 200

@categories_bp.route('/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """Get a specific category by ID"""
    current_user_id = get_jwt_identity()
    
    category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    return jsonify({"category": category.to_dict()}), 200

@categories_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    """Create a new transaction category"""
    current_user_id = get_jwt_identity()
    
    # Validate input data
    schema = CategorySchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Map string category type to enum
    try:
        category_type = CategoryType(data['type'])
    except ValueError:
        return jsonify({"message": "Invalid category type"}), 400
    
    # Check if category with same name and type already exists
    existing_category = Category.query.filter_by(
        name=data['name'], 
        type=category_type,
        user_id=current_user_id
    ).first()
    
    if existing_category:
        return jsonify({"message": "Category with this name and type already exists"}), 409
    
    # Create new category
    try:
        category = Category(
            name=data['name'],
            type=category_type,
            user_id=current_user_id,
            icon=data.get('icon'),
            color=data.get('color')
        )
        category.save()
        
        return jsonify({
            "message": "Category created successfully",
            "category": category.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({"message": "Failed to create category", "error": str(e)}), 500

@categories_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """Update an existing category"""
    current_user_id = get_jwt_identity()
    
    # Check if category exists and belongs to user
    category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    # Validate input data
    schema = CategorySchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Update category fields
    if 'name' in data:
        category.name = data['name']
    if 'type' in data:
        try:
            new_type = CategoryType(data['type'])
            category.type = new_type
        except ValueError:
            return jsonify({"message": "Invalid category type"}), 400
    if 'icon' in data:
        category.icon = data['icon']
    if 'color' in data:
        category.color = data['color']
    
    # Check for duplicate after update
    if 'name' in data or 'type' in data:
        existing_category = Category.query.filter_by(
            name=category.name, 
            type=category.type,
            user_id=current_user_id
        ).first()
        
        if existing_category and existing_category.id != category_id:
            return jsonify({"message": "Category with this name and type already exists"}), 409
    
    category.save()
    
    return jsonify({
        "message": "Category updated successfully",
        "category": category.to_dict()
    }), 200

@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category"""
    current_user_id = get_jwt_identity()
    
    # Check if category exists and belongs to user
    category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    # Check if category is in use by any transactions
    if category.transactions:
        return jsonify({
            "message": "Cannot delete category because it is assigned to transactions",
            "transaction_count": len(category.transactions)
        }), 400
    
    # Delete category
    try:
        category.delete()
        return jsonify({"message": "Category deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to delete category", "error": str(e)}), 500 