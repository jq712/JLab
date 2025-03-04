from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
import enum
from . import db, BaseModel
from datetime import datetime

class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PDFStatement(db.Model, BaseModel):
    """PDF Statement model for tracking uploaded bank statements"""
    __tablename__ = 'pdf_statements'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_error = Column(Text)
    
    # Metadata about the statement
    statement_date = Column(DateTime)
    institution = Column(String(100))
    account_number_last4 = Column(String(4))
    
    # Foreign keys
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationships
    account = relationship("Account")
    user = relationship("User", backref="pdf_statements")
    
    def __init__(self, filename, file_path, original_filename, account_id, user_id,
                institution=None, account_number_last4=None, statement_date=None):
        self.filename = filename
        self.file_path = file_path
        self.original_filename = original_filename
        self.account_id = account_id
        self.user_id = user_id
        self.institution = institution
        self.account_number_last4 = account_number_last4
        self.statement_date = statement_date
    
    def update_processing_status(self, status, error=None):
        """Update processing status and error message if any"""
        self.processing_status = status
        if error:
            self.processing_error = error
        db.session.commit()
    
    def to_dict(self):
        """Convert PDF statement object to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processing_status': self.processing_status.value,
            'processing_error': self.processing_error,
            'statement_date': self.statement_date.isoformat() if self.statement_date else None,
            'institution': self.institution,
            'account_number_last4': self.account_number_last4,
            'account_id': self.account_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<PDFStatement {self.original_filename} ({self.processing_status.value})>' 