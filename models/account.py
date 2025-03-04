from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from . import db, BaseModel

class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

class Account(db.Model, BaseModel):
    """Account model for financial accounts"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    balance = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    description = Column(String(255))
    institution = Column(String(100))
    is_active = Column(Integer, default=1)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationship with User
    user = relationship("User", backref="accounts")
    
    # Relationship with Transaction
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    
    def __init__(self, name, account_type, user_id, balance=0.0, currency="USD", 
                 description=None, institution=None):
        self.name = name
        self.account_type = account_type
        self.user_id = user_id
        self.balance = balance
        self.currency = currency
        self.description = description
        self.institution = institution
    
    def update_balance(self, amount):
        """Update account balance"""
        self.balance += amount
        db.session.commit()
    
    def to_dict(self):
        """Convert account object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'account_type': self.account_type.value,
            'balance': self.balance,
            'currency': self.currency,
            'description': self.description,
            'institution': self.institution,
            'is_active': self.is_active,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Account {self.name} ({self.account_type.value})>' 