from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text, Boolean
from sqlalchemy.orm import relationship
from . import db, BaseModel
from datetime import date

class Transaction(db.Model, BaseModel):
    """Transaction model for tracking income and expenses"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=date.today)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    notes = Column(Text)
    is_reconciled = Column(Boolean, default=False)
    
    # Foreign keys
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    user = relationship("User", backref="transactions")
    
    def __init__(self, date, description, amount, account_id, category_id, user_id, 
                 notes=None, is_reconciled=False):
        self.date = date
        self.description = description
        self.amount = amount
        self.account_id = account_id
        self.category_id = category_id
        self.user_id = user_id
        self.notes = notes
        self.is_reconciled = is_reconciled
    
    def save(self):
        """Override save method to update account balance"""
        # First-time save (new transaction)
        if not self.id:
            db.session.add(self)
            # Update account balance
            self.account.update_balance(self.amount)
        db.session.commit()
    
    def delete(self):
        """Override delete method to update account balance"""
        # Reverse the transaction amount from account
        self.account.update_balance(-self.amount)
        db.session.delete(self)
        db.session.commit()
    
    def update_amount(self, new_amount):
        """Update transaction amount and account balance"""
        old_amount = self.amount
        self.amount = new_amount
        # Update account balance with the difference
        self.account.update_balance(new_amount - old_amount)
        db.session.commit()
    
    def to_dict(self):
        """Convert transaction object to dictionary"""
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'description': self.description,
            'amount': self.amount,
            'notes': self.notes,
            'is_reconciled': self.is_reconciled,
            'account_id': self.account_id,
            'category_id': self.category_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Transaction {self.description} ({self.amount})>' 