import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'inventory.db')

def initialize_database():
    print(f"Connecting to database at {DATABASE_PATH}...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        description TEXT
    );
    """)

    # Create Invoices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL
    );
    """)

    # Create Invoice Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
    );
    """)

    # Sample product data
    sample_products = [
        # (barcode, name, price, stock, description)
        ('8901234567890', 'Premium Milk (1L)', 60.0, 50, 'Fresh pasteurized whole milk'),
        ('8901111222233', 'Whole Wheat Bread (400g)', 45.0, 30, 'High-fiber sliced wheat bread'),
        ('8904444555566', 'Organic Eggs (Pack of 6)', 90.0, 15, 'Farm-fresh organic brown eggs'),
        ('1001', 'Potato Chips Classic (50g)', 20.0, 100, 'Crispy salted potato chips'),
        ('1002', 'Chocolate Chip Cookies', 35.0, 40, 'Delicious cookies with real chocolate chips'),
        ('1003', 'Instant Oats (500g)', 120.0, 25, 'Quick cooking healthy rolled oats'),
        ('1004', 'Tomato Ketchup (500g)', 99.0, 5, 'Sweet and tangy tomato ketchup (Low Stock Alert)'),
        ('1005', 'Sparkling Cola (250ml)', 25.0, 80, 'Refreshing carbonated soft drink'),
        ('1006', 'Green Tea Extract (25 Bags)', 150.0, 12, 'Pure organic green tea bags'),
        ('1007', 'Liquid Hand Wash (200ml)', 85.0, 3, 'Anti-bacterial hand sanitizer wash (Low Stock Alert)'),
    ]

    # Insert sample products
    for product in sample_products:
        try:
            cursor.execute("""
            INSERT OR IGNORE INTO products (barcode, name, price, stock, description)
            VALUES (?, ?, ?, ?, ?);
            """, product)
        except sqlite3.Error as e:
            print(f"Error inserting product {product[1]}: {e}")

    conn.commit()
    
    # Check count of products
    cursor.execute("SELECT COUNT(*) FROM products;")
    count = cursor.fetchone()[0]
    print(f"Database initialized successfully with {count} products.")
    
    conn.close()

if __name__ == '__main__':
    initialize_database()
