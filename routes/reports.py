from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from models.transaction import Transaction
from models.category import Category, CategoryType
from models.account import Account
from models.bill import Bill
from datetime import datetime, date, timedelta
import calendar

# Create blueprint
reports_bp = Blueprint('reports', __name__)

# Helper functions
def get_date_range_from_params():
    """Get start and end dates from request parameters"""
    # Default to current month if not specified
    today = date.today()
    default_start = date(today.year, today.month, 1)
    default_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    try:
        if 'start_date' in request.args:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        else:
            start_date = default_start
            
        if 'end_date' in request.args:
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        else:
            end_date = default_end
    except ValueError:
        # Invalid date format, use defaults
        start_date = default_start
        end_date = default_end
    
    return start_date, end_date

# Route definitions
@reports_bp.route('/spending-by-category', methods=['GET'])
@jwt_required()
def spending_by_category():
    """Get spending summarized by category for a given date range"""
    current_user_id = get_jwt_identity()
    start_date, end_date = get_date_range_from_params()
    
    # Get all expense transactions (negative amounts) for the date range
    # Join with categories to filter by expense type
    results = Transaction.query.join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == current_user_id,
        Transaction.date.between(start_date, end_date),
        Category.type == CategoryType.EXPENSE
    ).with_entities(
        Category.id,
        Category.name,
        Category.color,
        func.abs(func.sum(Transaction.amount)).label('total')
    ).group_by(
        Category.id,
        Category.name,
        Category.color
    ).order_by(
        desc('total')
    ).all()
    
    categories = []
    total_spending = 0
    
    for result in results:
        category = {
            'id': result.id,
            'name': result.name,
            'color': result.color,
            'total': float(result.total)
        }
        total_spending += float(result.total)
        categories.append(category)
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'categories': categories,
        'total_spending': total_spending
    }), 200

@reports_bp.route('/income-vs-expenses', methods=['GET'])
@jwt_required()
def income_vs_expenses():
    """Get income versus expenses comparison for a given date range"""
    current_user_id = get_jwt_identity()
    start_date, end_date = get_date_range_from_params()
    
    # Get summary by category type (income vs expense)
    results = Transaction.query.join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == current_user_id,
        Transaction.date.between(start_date, end_date)
    ).with_entities(
        Category.type,
        func.sum(Transaction.amount).label('total')
    ).group_by(
        Category.type
    ).all()
    
    income = 0
    expenses = 0
    
    for result in results:
        if result.type == CategoryType.INCOME:
            income = float(result.total)
        elif result.type == CategoryType.EXPENSE:
            expenses = float(abs(result.total))
    
    net = income - expenses
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'income': income,
        'expenses': expenses,
        'net': net
    }), 200

@reports_bp.route('/account-balances', methods=['GET'])
@jwt_required()
def account_balances():
    """Get summary of all account balances"""
    current_user_id = get_jwt_identity()
    
    # Get all active accounts
    accounts = Account.query.filter_by(
        user_id=current_user_id,
        is_active=1
    ).all()
    
    # Separate accounts by type
    account_groups = {}
    total_balances = {}
    total_net_worth = 0
    
    for account in accounts:
        account_type = account.account_type.value
        if account_type not in account_groups:
            account_groups[account_type] = []
            total_balances[account_type] = 0
        
        account_data = {
            'id': account.id,
            'name': account.name,
            'balance': account.balance,
            'currency': account.currency,
            'institution': account.institution
        }
        
        account_groups[account_type].append(account_data)
        total_balances[account_type] += account.balance
        
        # For net worth calculation (credit card balances are negative)
        if account_type == 'credit_card':
            total_net_worth -= account.balance
        else:
            total_net_worth += account.balance
    
    return jsonify({
        'account_groups': account_groups,
        'total_balances': total_balances,
        'total_net_worth': total_net_worth
    }), 200

@reports_bp.route('/bill-summary', methods=['GET'])
@jwt_required()
def bill_summary():
    """Get summary of upcoming bills"""
    current_user_id = get_jwt_identity()
    
    # Get current date and date 30 days in future
    today = date.today()
    end_date = today + timedelta(days=30)
    
    # Get all unpaid bills due in the next 30 days
    upcoming_bills = Bill.query.filter(
        Bill.user_id == current_user_id,
        Bill.is_paid == False,
        Bill.due_date.between(today, end_date)
    ).order_by(
        Bill.due_date
    ).all()
    
    # Calculate total amount due
    total_due = sum(bill.amount for bill in upcoming_bills)
    
    bills_data = []
    for bill in upcoming_bills:
        days_until_due = (bill.due_date - today).days
        bills_data.append({
            'id': bill.id,
            'name': bill.name,
            'amount': bill.amount,
            'due_date': bill.due_date.isoformat(),
            'days_until_due': days_until_due,
            'category_id': bill.category_id
        })
    
    # Get overdue bills
    overdue_bills = Bill.query.filter(
        Bill.user_id == current_user_id,
        Bill.is_paid == False,
        Bill.due_date < today
    ).order_by(
        Bill.due_date
    ).all()
    
    overdue_data = []
    overdue_total = 0
    for bill in overdue_bills:
        days_overdue = (today - bill.due_date).days
        overdue_data.append({
            'id': bill.id,
            'name': bill.name,
            'amount': bill.amount,
            'due_date': bill.due_date.isoformat(),
            'days_overdue': days_overdue,
            'category_id': bill.category_id
        })
        overdue_total += bill.amount
    
    return jsonify({
        'upcoming_bills': bills_data,
        'upcoming_total': total_due,
        'overdue_bills': overdue_data,
        'overdue_total': overdue_total
    }), 200

@reports_bp.route('/monthly-trend', methods=['GET'])
@jwt_required()
def monthly_trend():
    """Get monthly income and expense trends"""
    current_user_id = get_jwt_identity()
    
    # Get number of months to look back (default 6)
    try:
        months = int(request.args.get('months', 6))
        if months < 1:
            months = 6
    except ValueError:
        months = 6
    
    today = date.today()
    start_month = today.month - months
    start_year = today.year
    
    # Adjust year if needed
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    
    start_date = date(start_year, start_month, 1)
    
    # Get monthly income and expense totals
    monthly_data = []
    
    current_date = start_date
    while current_date <= today:
        month_name = current_date.strftime('%B %Y')
        month_start = date(current_date.year, current_date.month, 1)
        month_end = date(
            current_date.year, current_date.month, 
            calendar.monthrange(current_date.year, current_date.month)[1]
        )
        
        # Get income for month
        income_result = Transaction.query.join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == current_user_id,
            Transaction.date.between(month_start, month_end),
            Category.type == CategoryType.INCOME
        ).with_entities(
            func.sum(Transaction.amount).label('total')
        ).first()
        
        income = float(income_result.total) if income_result.total else 0
        
        # Get expenses for month
        expense_result = Transaction.query.join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == current_user_id,
            Transaction.date.between(month_start, month_end),
            Category.type == CategoryType.EXPENSE
        ).with_entities(
            func.sum(Transaction.amount).label('total')
        ).first()
        
        expenses = float(abs(expense_result.total)) if expense_result.total else 0
        
        monthly_data.append({
            'month': month_name,
            'income': income,
            'expenses': expenses,
            'net': income - expenses
        })
        
        # Move to next month
        month = current_date.month + 1
        year = current_date.year
        if month > 12:
            month = 1
            year += 1
        
        current_date = date(year, month, 1)
    
    return jsonify({
        'monthly_trend': monthly_data
    }), 200 