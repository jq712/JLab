"""Simple database connection utility"""
import os
import pymysql
from pymysql.cursors import DictCursor


def get_connection(config):
    """Get a database connection"""
    # Parse database URI - expected format: mysql+pymysql://username:password@host/dbname
    uri = config['DATABASE_URI']
    uri = uri.replace('mysql+pymysql://', '')
    auth, rest = uri.split('@')
    username, password = auth.split(':')
    host, dbname = rest.split('/')
    
    return pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=dbname,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False
    )


def execute_query(connection, query, params=None):
    """Execute a query and return the cursor"""
    with connection.cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor


def fetch_all(connection, query, params=None):
    """Execute a query and fetch all results"""
    cursor = execute_query(connection, query, params)
    return cursor.fetchall()


def fetch_one(connection, query, params=None):
    """Execute a query and fetch one result"""
    cursor = execute_query(connection, query, params)
    return cursor.fetchone()


def execute_with_commit(connection, query, params=None):
    """Execute a query and commit the transaction"""
    try:
        execute_query(connection, query, params)
        connection.commit()
    except:
        connection.rollback()
        raise 