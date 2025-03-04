# Personal Finance Management - Backend

A Flask-based backend API for a personal finance management application.

## Features

- User authentication and authorization
- Account management (checking, savings, credit cards, etc.)
- Transaction tracking and categorization
- Bill management and reminders
- PDF statement processing and data extraction
- Financial reporting and data visualization

## Project Structure

- `app.py`: Main application entry point
- `config.py`: Application configuration
- `models/`: Database models
- `routes/`: API route definitions
- `services/`: Business logic services
- `utils/`: Utility functions

## Setup Instructions

1. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the following variables:

   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   DATABASE_URI=mysql+pymysql://username:password@localhost/finance_db
   JWT_SECRET_KEY=your_jwt_secret_key
   ```

4. Initialize the database:

   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. Run the application:
   ```
   flask run
   ```

## API Documentation

The API will be accessible at `http://localhost:5000/api/` with the following endpoints:

- Auth: `/api/auth/` (register, login, refresh)
- Users: `/api/users/` (user profile management)
- Accounts: `/api/accounts/` (financial accounts)
- Transactions: `/api/transactions/` (income and expenses)
- Categories: `/api/categories/` (transaction categories)
- Bills: `/api/bills/` (bill tracking)
- Reports: `/api/reports/` (financial reports)
- PDF Processing: `/api/pdf/` (statement processing)
