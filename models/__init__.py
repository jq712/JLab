from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class BaseModel:
    """Base model for all database models"""
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def save(self):
        """Save the model instance to database"""
        db.session.add(self)
        db.session.commit()
        
    def delete(self):
        """Delete the model instance from database"""
        db.session.delete(self)
        db.session.commit()
        
    @classmethod
    def get_all(cls):
        """Get all records of this model"""
        return cls.query.all()
    
    @classmethod
    def get_by_id(cls, id):
        """Get record by ID"""
        return cls.query.get(id)
    
    @classmethod
    def get_by_filter(cls, **kwargs):
        """Get records by filter"""
        return cls.query.filter_by(**kwargs).all() 