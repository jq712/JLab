# Personal Finance Management - Backend

A Flask-based backend API for a personal finance management application designed for family use.

## Features

- User authentication and authorization
- Account management (checking, savings, credit cards, etc.)
- Transaction tracking and categorization
- Bill management and reminders
- PDF statement processing and data extraction
- Financial reporting and data visualization
- Family-wide access to all financial data

## Project Structure

- `app.py`: Main application entry point
- `config.py`: Application configuration
- `models/`: Database models
- `routes/`: API route definitions
- `services/`: Business logic services
- `utils/`: Utility functions and database helpers

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
   python -m utils.db_init
   ```

5. Run the application:
   ```
   flask run
   ```

## API Documentation

The API will be accessible at `http://localhost:5000/api/` with the following endpoints:

### Authentication

- `POST /api/auth/register`: Register a new user
- `POST /api/auth/login`: Login and get access token
- `POST /api/auth/refresh`: Refresh access token
- `GET /api/auth/me`: Get current user information

### Users

- `GET /api/users`: Get all users
- `GET /api/users/<id>`: Get user by ID
- `PUT /api/users/<id>`: Update user
- `DELETE /api/users/<id>`: Delete user

### Accounts

- `GET /api/accounts`: Get all accounts
- `POST /api/accounts`: Create new account
- `GET /api/accounts/<id>`: Get account by ID
- `PUT /api/accounts/<id>`: Update account
- `DELETE /api/accounts/<id>`: Delete account

### Transactions

- `GET /api/transactions`: Get all transactions
- `POST /api/transactions`: Create new transaction
- `GET /api/transactions/<id>`: Get transaction by ID
- `PUT /api/transactions/<id>`: Update transaction
- `DELETE /api/transactions/<id>`: Delete transaction
- `GET /api/transactions/account/<account_id>`: Get transactions by account

### Categories

- `GET /api/categories`: Get all categories
- `POST /api/categories`: Create new category
- `GET /api/categories/<id>`: Get category by ID
- `PUT /api/categories/<id>`: Update category
- `DELETE /api/categories/<id>`: Delete category

### Bills

- `GET /api/bills`: Get all bills
- `POST /api/bills`: Create new bill
- `GET /api/bills/<id>`: Get bill by ID
- `PUT /api/bills/<id>`: Update bill
- `DELETE /api/bills/<id>`: Delete bill
- `GET /api/bills/upcoming`: Get upcoming bills

### Reports

- `GET /api/reports/spending`: Get spending reports
- `GET /api/reports/income`: Get income reports
- `GET /api/reports/balance`: Get balance reports

### PDF Processing

- `POST /api/pdf/upload`: Upload PDF statement
- `GET /api/pdf/statements`: Get all PDF statements
- `GET /api/pdf/statements/<id>`: Get PDF statement by ID
- `POST /api/pdf/process/<id>`: Process PDF statement

## Security

This application is designed for family use, where all registered users have full access to all financial data. Strong security measures are in place to protect against unauthorized external access, including:

- JWT-based authentication
- Password hashing
- HTTPS support
- Input validation
- Parameterized SQL queries to prevent SQL injection

## Database

The application uses raw SQL with PyMySQL for database operations, providing:

- Direct control over database queries
- Optimized performance
- Transparent database operations
- Transaction support
