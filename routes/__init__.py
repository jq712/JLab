from flask import Blueprint

def register_routes(app):
    """Register all API routes with the Flask application"""
    
    # Import route modules
    from .auth import auth_bp
    from .users import users_bp
    from .accounts import accounts_bp
    from .transactions import transactions_bp
    from .categories import categories_bp
    from .bills import bills_bp
    from .reports import reports_bp
    from .pdf import pdf_bp
    
    # Register blueprints with API prefix
    api_prefix = app.config['API_PREFIX']
    
    app.register_blueprint(auth_bp, url_prefix=f'{api_prefix}/auth')
    app.register_blueprint(users_bp, url_prefix=f'{api_prefix}/users')
    app.register_blueprint(accounts_bp, url_prefix=f'{api_prefix}/accounts')
    app.register_blueprint(transactions_bp, url_prefix=f'{api_prefix}/transactions')
    app.register_blueprint(categories_bp, url_prefix=f'{api_prefix}/categories')
    app.register_blueprint(bills_bp, url_prefix=f'{api_prefix}/bills')
    app.register_blueprint(reports_bp, url_prefix=f'{api_prefix}/reports')
    app.register_blueprint(pdf_bp, url_prefix=f'{api_prefix}/pdf') 