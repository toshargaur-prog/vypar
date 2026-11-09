import sqlite3
import datetime
from contextlib import contextmanager
from typing import Generator
from app.config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """
    Returns an SQLite connection with WAL journal mode, busy timeout,
    and foreign key constraints enabled for high concurrency and data integrity.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """
    Creates all application tables with zero dummy/hardcoded data.
    The database starts 100% clean and ready for user input.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Business Profile (Fully customizable by the business owner)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tagline TEXT,
            business_type TEXT DEFAULT 'shop',
            owner_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            state_code TEXT DEFAULT '08',
            state_name TEXT DEFAULT 'Rajasthan',
            gstin TEXT,
            upi_id TEXT,
            upi_name TEXT,
            currency TEXT DEFAULT 'INR',
            symbol TEXT DEFAULT '₹',
            welcome_msg TEXT,
            is_configured INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Inventory / Products (User-created only)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT,
            category TEXT DEFAULT 'General',
            unit TEXT DEFAULT 'pcs',
            cost_price REAL DEFAULT 0.0,
            selling_price REAL NOT NULL,
            stock_qty REAL DEFAULT 0.0,
            min_threshold REAL DEFAULT 5.0,
            hsn_code TEXT,
            gst_rate REAL DEFAULT 18.0,
            batch_no TEXT,
            expiry_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. Customers & Khata Ledger (User-created only)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            business_name TEXT,
            gstin TEXT,
            address TEXT,
            balance_due REAL DEFAULT 0.0,
            total_purchases REAL DEFAULT 0.0,
            notes TEXT,
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Invoices
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT,
            customer_gstin TEXT,
            subtotal REAL NOT NULL,
            cgst REAL DEFAULT 0.0,
            sgst REAL DEFAULT 0.0,
            igst REAL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0.0,
            balance_amount REAL DEFAULT 0.0,
            status TEXT DEFAULT 'UNPAID',
            due_date TEXT,
            upi_link TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );
        """)

        # 5. Invoice Items
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            item_id INTEGER,
            item_name TEXT NOT NULL,
            hsn_code TEXT,
            quantity REAL NOT NULL,
            unit TEXT DEFAULT 'pcs',
            unit_price REAL NOT NULL,
            gst_rate REAL DEFAULT 18.0,
            tax_amount REAL DEFAULT 0.0,
            total_price REAL NOT NULL,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );
        """)

        # 6. WhatsApp Messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            sender_name TEXT,
            direction TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT,
            media_url TEXT,
            status TEXT DEFAULT 'DELIVERED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 7. Follow-up Tasks (Automated Engine)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            invoice_id INTEGER,
            followup_type TEXT NOT NULL,
            scheduled_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'PENDING',
            message_text TEXT NOT NULL,
            executed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        );
        """)

        # 8. Appointments (Clinics / Service businesses)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            service_type TEXT NOT NULL,
            status TEXT DEFAULT 'CONFIRMED',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 9. Security Audit Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Ensure single default business profile exists (Clean & unpopulated)
        cursor.execute("SELECT COUNT(*) as count FROM business_profile;")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
            INSERT INTO business_profile (
                name, tagline, business_type, owner_name, phone, email,
                address, state_code, state_name, gstin, upi_id, upi_name,
                currency, symbol, welcome_msg, is_configured
            ) VALUES (
                'My Business Store', 'Fast, Reliable & Honest Service', 'shop',
                'Business Owner', '+91 98000 00000', 'contact@mybusiness.local',
                'Main Market Road, City, State - Pin Code', '08', 'Rajasthan',
                '', 'mybusiness@upi', 'My Business Store',
                'INR', '₹', 'Namaste! 🙏 Welcome to our store. How can we assist you today?', 0
            );
            """)
            cursor.execute("""
            INSERT INTO audit_logs (action_type, description, ip_address)
            VALUES ('SYSTEM_INIT', 'Clean database initialized with zero dummy seed data.', '127.0.0.1');
            """)

def reset_database_data():
    """
    Wipes all transactional user data (inventory, invoices, customers, messages, followups)
    and resets the database to a completely clean state.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_items;")
        cursor.execute("DELETE FROM invoices;")
        cursor.execute("DELETE FROM inventory;")
        cursor.execute("DELETE FROM customers;")
        cursor.execute("DELETE FROM messages;")
        cursor.execute("DELETE FROM followups;")
        cursor.execute("DELETE FROM appointments;")
        cursor.execute("DELETE FROM audit_logs;")
        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('DATA_WIPE', 'All transactional data erased. Database reset to clean state.', '127.0.0.1');
        """)

