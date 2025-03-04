from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from . import db, BaseModel
from datetime import date

class BillFrequency(enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class Bill(db.Model, BaseModel):
    """Bill model for tracking recurring and one-time bills"""
    __tablename__ = 'bills'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    frequency = Column(Enum(BillFrequency), nullable=False, default=BillFrequency.MONTHLY)
    is_paid = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Foreign keys
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'))  # Optional, for linked account
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationships
    category = relationship("Category")
    account = relationship("Account")
    user = relationship("User", backref="bills")
    
    def __init__(self, name, amount, due_date, frequency, category_id, user_id, 
                 account_id=None, is_paid=False, notes=None):
        self.name = name
        self.amount = amount
        self.due_date = due_date
        self.frequency = frequency
        self.category_id = category_id
        self.user_id = user_id
        self.account_id = account_id
        self.is_paid = is_paid
        self.notes = notes
    
    def mark_as_paid(self):
        """Mark the bill as paid"""
        self.is_paid = True
        db.session.commit()
    
    def mark_as_unpaid(self):
        """Mark the bill as unpaid"""
        self.is_paid = False
        db.session.commit()
    
    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency"""
        from datetime import timedelta
        
        if self.frequency == BillFrequency.ONCE:
            return None  # No next due date for one-time bills
        
        current_due_date = self.due_date
        today = date.today()
        
        if current_due_date < today:
            # If due date is in the past, calculate from there
            while current_due_date < today:
                if self.frequency == BillFrequency.DAILY:
                    current_due_date += timedelta(days=1)
                elif self.frequency == BillFrequency.WEEKLY:
                    current_due_date += timedelta(weeks=1)
                elif self.frequency == BillFrequency.BIWEEKLY:
                    current_due_date += timedelta(weeks=2)
                elif self.frequency == BillFrequency.MONTHLY:
                    # Approximate a month as 30 days
                    month = current_due_date.month + 1
                    year = current_due_date.year
                    if month > 12:
                        month = 1
                        year += 1
                    day = min(current_due_date.day, 28 if month == 2 else 30)
                    current_due_date = date(year, month, day)
                elif self.frequency == BillFrequency.QUARTERLY:
                    # Approximate a quarter as 3 months
                    month = current_due_date.month + 3
                    year = current_due_date.year
                    if month > 12:
                        month = month - 12
                        year += 1
                    day = min(current_due_date.day, 28 if month == 2 else 30)
                    current_due_date = date(year, month, day)
                elif self.frequency == BillFrequency.YEARLY:
                    # Increment year by 1
                    current_due_date = date(current_due_date.year + 1, 
                                          current_due_date.month, 
                                          current_due_date.day)
        
        return current_due_date
    
    def to_dict(self):
        """Convert bill object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'due_date': self.due_date.isoformat(),
            'frequency': self.frequency.value,
            'is_paid': self.is_paid,
            'notes': self.notes,
            'category_id': self.category_id,
            'account_id': self.account_id,
            'user_id': self.user_id,
            'next_due_date': self.calculate_next_due_date().isoformat() if self.calculate_next_due_date() else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f'<Bill {self.name} ({self.amount})>' 