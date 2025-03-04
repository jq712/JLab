from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from . import db, BaseModel

class CategoryType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Category(db.Model, BaseModel):
    """Category model for transaction categories"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    icon = Column(String(50))
    color = Column(String(7))  # Hex color code (e.g., #FF5733)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationship with User
    user = relationship("User", backref="categories")
    
    # Relationship with Transaction
    transactions = relationship("Transaction", back_populates="category")
    
    def __init__(self, name, type, user_id, icon=None, color=None):
        self.name = name
        self.type = type
        self.user_id = user_id
        self.icon = icon
        self.color = color
    
    def to_dict(self):
        """Convert category object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'icon': self.icon,
            'color': self.color,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Category {self.name} ({self.type.value})>' 