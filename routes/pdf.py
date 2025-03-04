import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models.pdf_statement import PDFStatement, ProcessingStatus
from models.account import Account
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

# Create blueprint
pdf_bp = Blueprint('pdf', __name__)

# Validation schema
class PDFUploadSchema(Schema):
    account_id = fields.Integer(required=True)
    statement_date = fields.Date()
    institution = fields.String()
    account_number_last4 = fields.String(validate=validate.Length(equal=4))

# Helper functions
def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Route definitions
@pdf_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_pdf():
    """Upload a PDF bank/credit card statement"""
    current_user_id = get_jwt_identity()
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request"}), 400
    
    file = request.files['file']
    
    # Check if user submitted an empty form
    if file.filename == '':
        return jsonify({"message": "No file selected"}), 400
    
    # Validate input data
    schema = PDFUploadSchema()
    try:
        data = schema.load(request.form)
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400
    
    # Verify account exists and belongs to user
    account = Account.query.filter_by(id=data['account_id'], user_id=current_user_id).first()
    if not account:
        return jsonify({"message": "Account not found or does not belong to you"}), 404
    
    # Check if file is a PDF
    if file and allowed_file(file.filename):
        # Secure the filename and generate a unique name
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}.pdf"
        
        # Save the file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Create database record
        try:
            statement_date = None
            if data.get('statement_date'):
                statement_date = data['statement_date']
            
            pdf_statement = PDFStatement(
                filename=filename,
                file_path=file_path,
                original_filename=original_filename,
                account_id=data['account_id'],
                user_id=current_user_id,
                institution=data.get('institution'),
                account_number_last4=data.get('account_number_last4'),
                statement_date=statement_date
            )
            pdf_statement.save()
            
            # Start background processing task (this would use a job queue in production)
            # For now, we'll just update the status (real processing would be implemented in services module)
            pdf_statement.update_processing_status(ProcessingStatus.PROCESSING)
            
            return jsonify({
                "message": "PDF statement uploaded successfully",
                "statement": pdf_statement.to_dict()
            }), 201
            
        except Exception as e:
            # Delete the file if database record creation fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"message": "Failed to process statement", "error": str(e)}), 500
    
    return jsonify({"message": "Invalid file format, only PDF files are allowed"}), 400

@pdf_bp.route('/statements', methods=['GET'])
@jwt_required()
def get_all_statements():
    """Get all PDF statements for the current user"""
    current_user_id = get_jwt_identity()
    
    # Filter by account if specified
    account_id = request.args.get('account_id')
    if account_id:
        try:
            account_id = int(account_id)
            statements = PDFStatement.query.filter_by(
                user_id=current_user_id, 
                account_id=account_id
            ).order_by(PDFStatement.uploaded_at.desc()).all()
        except ValueError:
            statements = PDFStatement.query.filter_by(
                user_id=current_user_id
            ).order_by(PDFStatement.uploaded_at.desc()).all()
    else:
        statements = PDFStatement.query.filter_by(
            user_id=current_user_id
        ).order_by(PDFStatement.uploaded_at.desc()).all()
    
    return jsonify({
        "statements": [statement.to_dict() for statement in statements]
    }), 200

@pdf_bp.route('/statements/<int:statement_id>', methods=['GET'])
@jwt_required()
def get_statement(statement_id):
    """Get a specific PDF statement by ID"""
    current_user_id = get_jwt_identity()
    
    statement = PDFStatement.query.filter_by(id=statement_id, user_id=current_user_id).first()
    if not statement:
        return jsonify({"message": "Statement not found"}), 404
    
    return jsonify({"statement": statement.to_dict()}), 200

@pdf_bp.route('/statements/<int:statement_id>/process', methods=['POST'])
@jwt_required()
def process_statement(statement_id):
    """Manually trigger processing of a PDF statement"""
    current_user_id = get_jwt_identity()
    
    statement = PDFStatement.query.filter_by(id=statement_id, user_id=current_user_id).first()
    if not statement:
        return jsonify({"message": "Statement not found"}), 404
    
    # Update status to processing
    statement.update_processing_status(ProcessingStatus.PROCESSING)
    
    # Here, you would trigger the actual processing job
    # For now, we'll just pretend it worked (real implementation in services module)
    statement.update_processing_status(ProcessingStatus.COMPLETED)
    
    return jsonify({
        "message": "Statement processing triggered successfully",
        "statement": statement.to_dict()
    }), 200

@pdf_bp.route('/statements/<int:statement_id>', methods=['DELETE'])
@jwt_required()
def delete_statement(statement_id):
    """Delete a PDF statement"""
    current_user_id = get_jwt_identity()
    
    statement = PDFStatement.query.filter_by(id=statement_id, user_id=current_user_id).first()
    if not statement:
        return jsonify({"message": "Statement not found"}), 404
    
    # Delete file from disk
    if os.path.exists(statement.file_path):
        os.remove(statement.file_path)
    
    # Delete database record
    try:
        statement.delete()
        return jsonify({"message": "Statement deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to delete statement", "error": str(e)}), 500 