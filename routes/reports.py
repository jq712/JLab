from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.transaction import Transaction
from models.category import Category, CategoryType
from models.account import Account
from models.bill import Bill
from utils.database import db
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
    query = """
        SELECT c.id, c.name, c.color, ABS(SUM(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        AND t.date BETWEEN %s AND %s
        AND c.type = %s
        AND t.amount < 0
        GROUP BY c.id, c.name, c.color
        ORDER BY total DESC
    """
    
    results = db.fetch_all(
        query, 
        (current_user_id, start_date.isoformat(), end_date.isoformat(), CategoryType.EXPENSE.value)
    )
    
    # Calculate total spending
    total_spending = sum(item['total'] for item in results)
    
    # Format response
    categories = []
    for item in results:
        categories.append({
            'id': item['id'],
            'name': item['name'],
            'color': item['color'],
            'amount': float(item['total']),
            'percentage': round((float(item['total']) / total_spending * 100), 2) if total_spending > 0 else 0
        })
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total': float(total_spending),
        'categories': categories
    }), 200

@reports_bp.route('/income-vs-expenses', methods=['GET'])
@jwt_required()
def income_vs_expenses():
    """Get income vs expenses summary for a given date range"""
    current_user_id = get_jwt_identity()
    start_date, end_date = get_date_range_from_params()
    
    # Get income (positive amounts)
    income_query = """
        SELECT SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        AND t.date BETWEEN %s AND %s
        AND c.type = %s
        AND t.amount > 0
    """
    
    income_result = db.fetch_one(
        income_query, 
        (current_user_id, start_date.isoformat(), end_date.isoformat(), CategoryType.INCOME.value)
    )
    
    # Get expenses (negative amounts, but we'll make them positive for display)
    expense_query = """
        SELECT ABS(SUM(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        AND t.date BETWEEN %s AND %s
        AND c.type = %s
        AND t.amount < 0
    """
    
    expense_result = db.fetch_one(
        expense_query, 
        (current_user_id, start_date.isoformat(), end_date.isoformat(), CategoryType.EXPENSE.value)
    )
    
    # Calculate totals and net
    total_income = float(income_result['total'] if income_result and income_result['total'] else 0)
    total_expenses = float(expense_result['total'] if expense_result and expense_result['total'] else 0)
    net = total_income - total_expenses
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'income': total_income,
        'expenses': total_expenses,
        'net': net
    }), 200

@reports_bp.route('/account-balances', methods=['GET'])
@jwt_required()
def account_balances():
    """Get current account balances"""
    current_user_id = get_jwt_identity()
    
    # Get all active accounts
    accounts = Account.get_active_by_user_id(current_user_id)
    
    # Format response
    account_balances = []
    total_balance = 0
    
    for account in accounts:
        balance = float(account.balance) if hasattr(account, 'balance') else 0
        account_balances.append({
            'id': account.id,
            'name': account.name,
            'type': account.account_type,
            'balance': balance,
            'currency': account.currency
        })
        total_balance += balance
    
    # Get recent transactions
    recent_query = """
        SELECT t.id, t.date, t.description, t.amount, a.name as account_name, c.name as category_name
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.date DESC
        LIMIT 5
    """
    
    recent_transactions = db.fetch_all(recent_query, (current_user_id,))
    
    # Format recent transactions
    recent = []
    for tx in recent_transactions:
        recent.append({
            'id': tx['id'],
            'date': tx['date'].isoformat() if isinstance(tx['date'], date) else tx['date'],
            'description': tx['description'],
            'amount': float(tx['amount']),
            'account_name': tx['account_name'],
            'category_name': tx['category_name']
        })
    
    return jsonify({
        'total_balance': total_balance,
        'accounts': account_balances,
        'recent_transactions': recent
    }), 200

@reports_bp.route('/bill-summary', methods=['GET'])
@jwt_required()
def bill_summary():
    """Get summary of upcoming bills"""
    current_user_id = get_jwt_identity()
    
    # Get upcoming bills (due in the next 30 days)
    today = date.today()
    end_date = today + timedelta(days=30)
    
    upcoming_query = """
        SELECT b.id, b.name, b.amount, b.due_date, b.frequency, b.is_paid,
               c.name as category_name, a.name as account_name
        FROM bills b
        LEFT JOIN categories c ON b.category_id = c.id
        LEFT JOIN accounts a ON b.account_id = a.id
        WHERE b.user_id = %s
        AND b.due_date BETWEEN %s AND %s
        ORDER BY b.due_date ASC
    """
    
    upcoming_bills = db.fetch_all(
        upcoming_query, 
        (current_user_id, today.isoformat(), end_date.isoformat())
    )
    
    # Get overdue bills
    overdue_query = """
        SELECT b.id, b.name, b.amount, b.due_date, b.frequency, b.is_paid,
               c.name as category_name, a.name as account_name
        FROM bills b
        LEFT JOIN categories c ON b.category_id = c.id
        LEFT JOIN accounts a ON b.account_id = a.id
        WHERE b.user_id = %s
        AND b.due_date < %s
        AND b.is_paid = 0
        ORDER BY b.due_date ASC
    """
    
    overdue_bills = db.fetch_all(overdue_query, (current_user_id, today.isoformat()))
    
    # Format response
    upcoming = []
    for bill in upcoming_bills:
        upcoming.append({
            'id': bill['id'],
            'name': bill['name'],
            'amount': float(bill['amount']),
            'due_date': bill['due_date'].isoformat() if isinstance(bill['due_date'], date) else bill['due_date'],
            'frequency': bill['frequency'],
            'is_paid': bool(bill['is_paid']),
            'category_name': bill['category_name'],
            'account_name': bill['account_name']
        })
    
    overdue = []
    for bill in overdue_bills:
        overdue.append({
            'id': bill['id'],
            'name': bill['name'],
            'amount': float(bill['amount']),
            'due_date': bill['due_date'].isoformat() if isinstance(bill['due_date'], date) else bill['due_date'],
            'frequency': bill['frequency'],
            'is_paid': bool(bill['is_paid']),
            'category_name': bill['category_name'],
            'account_name': bill['account_name']
        })
    
    # Calculate totals
    total_upcoming = sum(bill['amount'] for bill in upcoming)
    total_overdue = sum(bill['amount'] for bill in overdue)
    
    return jsonify({
        'upcoming_bills': upcoming,
        'overdue_bills': overdue,
        'total_upcoming': float(total_upcoming),
        'total_overdue': float(total_overdue)
    }), 200

@reports_bp.route('/monthly-trend', methods=['GET'])
@jwt_required()
def monthly_trend():
    """Get monthly income and expense trends for the past 6 months"""
    current_user_id = get_jwt_identity()
    
    # Calculate date range (past 6 months)
    end_date = date.today()
    start_date = date(end_date.year - 1 if end_date.month <= 6 else end_date.year, 
                     (end_date.month - 6) % 12 + 1, 1)
    
    # Get monthly income
    income_query = """
        SELECT 
            YEAR(t.date) as year,
            MONTH(t.date) as month,
            SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        AND t.date BETWEEN %s AND %s
        AND c.type = %s
        AND t.amount > 0
        GROUP BY YEAR(t.date), MONTH(t.date)
        ORDER BY YEAR(t.date), MONTH(t.date)
    """
    
    income_results = db.fetch_all(
        income_query, 
        (current_user_id, start_date.isoformat(), end_date.isoformat(), CategoryType.INCOME.value)
    )
    
    # Get monthly expenses
    expense_query = """
        SELECT 
            YEAR(t.date) as year,
            MONTH(t.date) as month,
            ABS(SUM(t.amount)) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        AND t.date BETWEEN %s AND %s
        AND c.type = %s
        AND t.amount < 0
        GROUP BY YEAR(t.date), MONTH(t.date)
        ORDER BY YEAR(t.date), MONTH(t.date)
    """
    
    expense_results = db.fetch_all(
        expense_query, 
        (current_user_id, start_date.isoformat(), end_date.isoformat(), CategoryType.EXPENSE.value)
    )
    
    # Create a dictionary of months for easy lookup
    months = {}
    current = start_date
    while current <= end_date:
        month_key = f"{current.year}-{current.month:02d}"
        months[month_key] = {
            'year': current.year,
            'month': current.month,
            'month_name': current.strftime('%b %Y'),
            'income': 0,
            'expenses': 0,
            'net': 0
        }
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    # Fill in income data
    for item in income_results:
        month_key = f"{item['year']}-{item['month']:02d}"
        if month_key in months:
            months[month_key]['income'] = float(item['total'])
    
    # Fill in expense data
    for item in expense_results:
        month_key = f"{item['year']}-{item['month']:02d}"
        if month_key in months:
            months[month_key]['expenses'] = float(item['total'])
    
    # Calculate net for each month
    for month_key in months:
        months[month_key]['net'] = months[month_key]['income'] - months[month_key]['expenses']
    
    # Convert to list and sort by date
    trend_data = list(months.values())
    trend_data.sort(key=lambda x: (x['year'], x['month']))
    
    return jsonify({
        'trend_data': trend_data
    }), 200 