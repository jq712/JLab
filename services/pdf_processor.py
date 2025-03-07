import os
import re
import tempfile
from datetime import datetime
import pandas as pd
import tabula
from pdfminer.high_level import extract_text
from models.pdf_statement import PDFStatement, ProcessingStatus

class PDFProcessor:
    """Service class for processing PDF bank/credit card statements"""
    
    def __init__(self, pdf_statement):
        """Initialize with a PDFStatement object"""
        if not isinstance(pdf_statement, PDFStatement):
            raise ValueError("Expected PDFStatement instance")
        
        self.pdf_statement = pdf_statement
        self.file_path = pdf_statement.file_path
        self.extracted_data = []
        
        # Bank-specific patterns
        self.bank_patterns = {
            'Chase': {
                'date_pattern': r'(\d{2}/\d{2}/\d{2,4})',
                'transaction_pattern': r'(\d{2}/\d{2}/\d{2,4})\s+([\w\s\'\-\&\/\.]+?)\s+([-+]?\$?[\d,]+\.\d{2})',
                'date_format': '%m/%d/%Y'
            },
            'Bank of America': {
                'date_pattern': r'(\d{2}/\d{2}/\d{2,4})',
                'transaction_pattern': r'(\d{2}/\d{2}/\d{2,4})\s+([\w\s\'\-\&\/\.]+?)\s+([-+]?\$?[\d,]+\.\d{2})',
                'date_format': '%m/%d/%Y'
            },
            'Wells Fargo': {
                'date_pattern': r'(\d{1,2}/\d{1,2}/\d{2,4})',
                'transaction_pattern': r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([\w\s\'\-\&\/\.]+?)\s+([-+]?\$?[\d,]+\.\d{2})',
                'date_format': '%m/%d/%Y'
            },
            # Add more banks as needed
        }
    
    def process(self):
        """Process the PDF statement and extract transactions"""
        try:
            # Update status to processing
            self.pdf_statement.update_processing_status(ProcessingStatus.PROCESSING)
            
            # First, detect the bank type (if possible)
            bank_type = self._detect_bank_type()
            
            # Try to extract data using tabula (table-based approach)
            self._extract_using_tabula()
            
            # If tabula didn't find enough data, try text-based extraction
            if len(self.extracted_data) < 5:  # Arbitrary threshold
                self._extract_using_text(bank_type)
            
            # Update status to completed
            self.pdf_statement.update_processing_status(ProcessingStatus.COMPLETED)
            
            return self.extracted_data
            
        except Exception as e:
            # Update status to failed
            self.pdf_statement.update_processing_status(ProcessingStatus.FAILED, str(e))
            raise
    
    def _detect_bank_type(self):
        """Attempt to detect which bank the statement is from"""
        try:
            # Extract text from the first page only
            text = extract_text(self.file_path, page_numbers=[0])
            
            # Check for bank names
            for bank_name in self.bank_patterns.keys():
                if bank_name.lower() in text.lower():
                    return bank_name
            
            # If not found, use the institution from the database record
            if self.pdf_statement.institution:
                return self.pdf_statement.institution
            
            # Default to generic processing
            return None
            
        except Exception:
            # If detection fails, return None for generic processing
            return None
    
    def _extract_using_tabula(self):
        """Extract transaction data using tabula (table-based approach)"""
        try:
            # Try to extract tables from the PDF
            tables = tabula.read_pdf(
                self.file_path,
                pages='all',
                multiple_tables=True,
                guess=True
            )
            
            if not tables:
                return
            
            # Process each table
            for table in tables:
                # Skip empty tables
                if table.empty:
                    continue
                
                # Clean up column names
                table.columns = [str(col).strip() for col in table.columns]
                
                # Look for date and amount columns
                date_col = None
                amount_col = None
                desc_col = None
                
                for col in table.columns:
                    col_lower = col.lower()
                    if any(date_term in col_lower for date_term in ['date', 'time']):
                        date_col = col
                    elif any(amount_term in col_lower for amount_term in ['amount', 'sum', 'total', 'payment', 'deposit']):
                        amount_col = col
                    elif any(desc_term in col_lower for desc_term in ['desc', 'transaction', 'activity', 'detail']):
                        desc_col = col
                
                # If we have at least date and amount columns, try to extract data
                if date_col and amount_col:
                    # If no description column was found, try to use the next column after date
                    if not desc_col and len(table.columns) > 2:
                        date_index = list(table.columns).index(date_col)
                        if date_index + 1 < len(table.columns):
                            desc_col = table.columns[date_index + 1]
                    
                    # Process rows
                    for _, row in table.iterrows():
                        try:
                            date_val = row[date_col]
                            amount_val = row[amount_col]
                            desc_val = row[desc_col] if desc_col else ""
                            
                            # Skip rows with missing data
                            if pd.isna(date_val) or pd.isna(amount_val):
                                continue
                            
                            # Clean up values
                            date_str = str(date_val)
                            amount_str = str(amount_val)
                            desc_str = str(desc_val) if not pd.isna(desc_val) else "Unknown transaction"
                            
                            # Parse date (try common formats)
                            transaction_date = None
                            for date_format in ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y']:
                                try:
                                    transaction_date = datetime.strptime(date_str, date_format).date()
                                    break
                                except ValueError:
                                    continue
                            
                            # Skip if date couldn't be parsed
                            if not transaction_date:
                                continue
                            
                            # Parse amount
                            amount_clean = re.sub(r'[^\d\.-]', '', amount_str)
                            try:
                                amount = float(amount_clean)
                            except ValueError:
                                continue
                            
                            # Add to extracted data
                            self.extracted_data.append({
                                'date': transaction_date,
                                'description': desc_str.strip(),
                                'amount': amount
                            })
                            
                        except Exception:
                            # Skip problematic rows
                            continue
            
        except Exception as e:
            # Log error but continue to text-based extraction
            print(f"Tabula extraction error: {str(e)}")
    
    def _extract_using_text(self, bank_type=None):
        """Extract transaction data using text-based approach"""
        try:
            # Extract text from the PDF
            text = extract_text(self.file_path)
            
            # Select the appropriate pattern based on bank type
            date_pattern = r'(\d{1,2}/\d{1,2}/\d{2,4})'
            transaction_pattern = r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([\w\s\'\-\&\/\.]+?)\s+([-+]?\$?[\d,]+\.\d{2})'
            date_format = '%m/%d/%Y'
            
            if bank_type and bank_type in self.bank_patterns:
                bank_config = self.bank_patterns[bank_type]
                date_pattern = bank_config['date_pattern']
                transaction_pattern = bank_config['transaction_pattern']
                date_format = bank_config['date_format']
            
            # Find transactions using regex pattern
            transactions = re.findall(transaction_pattern, text)
            
            for transaction in transactions:
                try:
                    date_str = transaction[0]
                    description = transaction[1].strip()
                    amount_str = transaction[2]
                    
                    # Parse date
                    transaction_date = datetime.strptime(date_str, date_format).date()
                    
                    # Parse amount
                    amount_clean = re.sub(r'[^\d\.-]', '', amount_str)
                    amount = float(amount_clean)
                    
                    # Determine if it's a positive or negative amount
                    if '-' in amount_str or '(' in amount_str:
                        amount = -abs(amount)
                    
                    # Add to extracted data
                    self.extracted_data.append({
                        'date': transaction_date,
                        'description': description,
                        'amount': amount
                    })
                    
                except Exception:
                    # Skip problematic transactions
                    continue
            
        except Exception as e:
            # Log error but continue
            print(f"Text extraction error: {str(e)}")
    
    @staticmethod
    def process_statement(pdf_statement_id, db):
        """Static method to process a statement by ID"""
        from models.pdf_statement import PDFStatement
        
        statement = PDFStatement.get_by_id(pdf_statement_id)
        if not statement:
            return False
        
        processor = PDFProcessor(statement)
        return processor.process() 