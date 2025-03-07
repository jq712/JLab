"""Database initialization script to set up tables using raw SQL"""
import os
import sys
from . import db
from config import get_config

# SQL statements to create tables
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        type ENUM('income', 'expense') NOT NULL,
        icon VARCHAR(50),
        color VARCHAR(10),
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        type ENUM('checking', 'savings', 'credit_card', 'cash', 'investment', 'other') NOT NULL,
        balance DECIMAL(15, 2) DEFAULT 0.00,
        currency VARCHAR(3) DEFAULT 'USD',
        description TEXT,
        institution VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL,
        description TEXT NOT NULL,
        amount DECIMAL(15, 2) NOT NULL,
        notes TEXT,
        is_reconciled BOOLEAN DEFAULT FALSE,
        account_id INT NOT NULL,
        category_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        amount DECIMAL(15, 2) NOT NULL,
        due_date DATE NOT NULL,
        frequency ENUM('once', 'daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly') NOT NULL,
        is_paid BOOLEAN DEFAULT FALSE,
        notes TEXT,
        category_id INT NOT NULL,
        account_id INT,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS pdf_statements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_path VARCHAR(512) NOT NULL,
        original_filename VARCHAR(255) NOT NULL,
        uploaded_at DATETIME NOT NULL,
        processing_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
        processing_error TEXT,
        statement_date DATE,
        institution VARCHAR(100),
        account_number_last4 VARCHAR(4),
        account_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
]

def initialize_database():
    """Initialize database by creating necessary tables"""
    config = get_config()
    conn = db.get_connection(config)
    
    try:
        # Create tables
        for table_sql in CREATE_TABLES:
            try:
                db.execute_with_commit(conn, table_sql)
                table_name = table_sql.strip().split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
                print(f"Table {table_name} created or already exists.")
            except Exception as e:
                print(f"Error creating table: {str(e)}")
                raise
        
        print("Database initialization complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database() 