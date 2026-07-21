from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import os
import datetime
import random

app = Flask(__name__)
app.secret_key = 'retail_scanner_secret_key_for_flash'

DATABASE = os.path.join(os.path.dirname(__file__), 'inventory.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Dashboard Route
@app.route('/')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Products
    cursor.execute("SELECT COUNT(*) FROM products;")
    total_products = cursor.fetchone()[0]
    
    # 2. Today's Sales
    cursor.execute("SELECT SUM(total_amount) FROM invoices WHERE date(created_at, 'localtime') = date('now', 'localtime');")
    today_sales_row = cursor.fetchone()
    today_sales = today_sales_row[0] if today_sales_row[0] is not None else 0.0
    
    # 3. Total Invoices
    cursor.execute("SELECT COUNT(*) FROM invoices;")
    total_invoices = cursor.fetchone()[0]
    
    # 4. Low Stock Count (Stock <= 5)
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 5;")
    low_stock_count = cursor.fetchone()[0]
    
    # 5. Recent Invoices
    cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5;")
    recent_invoices = [dict(row) for row in cursor.fetchall()]
    # Format datetime strings for better readability
    for inv in recent_invoices:
        dt = datetime.datetime.fromisoformat(inv['created_at'].replace('Z', '+00:00') if 'Z' in inv['created_at'] else inv['created_at'])
        inv['created_at'] = dt.strftime('%d-%b-%Y %I:%M %p')
        
    # 6. Low Stock Products
    cursor.execute("SELECT * FROM products WHERE stock <= 5 ORDER BY stock ASC LIMIT 5;")
    low_stock_products = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    stats = {
        'total_products': total_products,
        'today_sales': today_sales,
        'total_invoices': total_invoices,
        'low_stock_count': low_stock_count
    }
    
    return render_template(
        'index.html', 
        active_page='dashboard', 
        stats=stats, 
        recent_invoices=recent_invoices, 
        low_stock_products=low_stock_products
    )

# Scanner / Billing Route
@app.route('/scanner')
def scanner():
    return render_template('scanner.html', active_page='scanner')

# Inventory Management Route
@app.route('/inventory')
def inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY name ASC;")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template('inventory.html', active_page='inventory', products=products)

# Add Product Route
@app.route('/inventory/add', methods=['POST'])
def add_product():
    barcode = request.form['barcode'].strip()
    name = request.form['name'].strip()
    price = float(request.form['price'])
    stock = int(request.form['stock'])
    description = request.form['description'].strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO products (barcode, name, price, stock, description) VALUES (?, ?, ?, ?, ?);",
            (barcode, name, price, stock, description if description else None)
        )
        conn.commit()
        flash('Product added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Error: A product with barcode "{barcode}" already exists.', 'error')
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('inventory'))

# Edit Product Route
@app.route('/inventory/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    barcode = request.form['barcode'].strip()
    name = request.form['name'].strip()
    price = float(request.form['price'])
    stock = int(request.form['stock'])
    description = request.form['description'].strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE products SET barcode = ?, name = ?, price = ?, stock = ?, description = ? WHERE id = ?;",
            (barcode, name, price, stock, description if description else None, product_id)
        )
        conn.commit()
        flash('Product updated successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Error: A product with barcode "{barcode}" already exists.', 'error')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('inventory'))

# Delete Product Route
@app.route('/inventory/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = ?;", (product_id,))
        conn.commit()
        flash('Product deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('inventory'))

# Invoices History Route
@app.route('/invoices')
def invoices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, 
               (SELECT SUM(quantity) FROM invoice_items WHERE invoice_id = i.id) as items_count 
        FROM invoices i 
        ORDER BY i.created_at DESC;
    """)
    rows = cursor.fetchall()
    invoices_list = []
    for row in rows:
        inv = dict(row)
        dt = datetime.datetime.fromisoformat(inv['created_at'].replace('Z', '+00:00') if 'Z' in inv['created_at'] else inv['created_at'])
        inv['created_at'] = dt.strftime('%d-%b-%Y %I:%M %p')
        inv['items_count'] = inv['items_count'] if inv['items_count'] is not None else 0
        invoices_list.append(inv)
        
    conn.close()
    return render_template('invoices.html', active_page='invoices', invoices=invoices_list)

# View Specific Invoice Details (Print receipt)
@app.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM invoices WHERE id = ?;", (invoice_id,))
    invoice_row = cursor.fetchone()
    if not invoice_row:
        conn.close()
        return "Invoice not found", 404
        
    invoice = dict(invoice_row)
    dt = datetime.datetime.fromisoformat(invoice['created_at'].replace('Z', '+00:00') if 'Z' in invoice['created_at'] else invoice['created_at'])
    invoice['created_at'] = dt.strftime('%d-%b-%Y %I:%M %p')
    
    cursor.execute("""
        SELECT ii.*, p.name as product_name, p.barcode as barcode 
        FROM invoice_items ii 
        LEFT JOIN products p ON ii.product_id = p.id 
        WHERE ii.invoice_id = ?;
    """)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Calculate receipt subtotal and tax values
    # Total GST is 18%, subtotal is sum of items price * qty
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * 0.18
    
    return render_template(
        'invoice.html', 
        active_page='invoices', 
        invoice=invoice, 
        items=items, 
        subtotal=subtotal, 
        tax=tax
    )

# --- API ENDPOINTS ---

# Lookup Product by Barcode API
@app.route('/api/product/<string:barcode>', methods=['GET'])
def get_product(barcode):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE barcode = ?;", (barcode.strip(),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify(dict(row))
    else:
        return jsonify({'error': 'Product not found'}), 404

# Checkout cart to create invoice API
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    if not data or 'items' not in data or len(data['items']) == 0:
        return jsonify({'error': 'Empty cart checkout requested.'}), 400
        
    items = data['items']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start Transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Verify stock levels first and calculate total
        subtotal = 0
        for item in items:
            cursor.execute("SELECT stock, price, name FROM products WHERE id = ?;", (item['id'],))
            prod = cursor.fetchone()
            if not prod:
                raise Exception(f"Product ID {item['id']} no longer exists in inventory.")
                
            available_stock = prod['stock']
            if available_stock < item['quantity']:
                raise Exception(f"Insufficient stock for {prod['name']}. Available: {available_stock}, Requested: {item['quantity']}")
            
            subtotal += prod['price'] * item['quantity']
            
        tax = subtotal * 0.18
        grand_total = subtotal + tax
        
        # Generate Invoice Number: INV-YYYYMMDD-XXXX (Random 4-digit sequence for mini-project simplicity)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        rand_suffix = random.randint(1000, 9999)
        invoice_number = f"INV-{date_str}-{rand_suffix}"
        
        # Insert Invoice
        cursor.execute(
            "INSERT INTO invoices (invoice_number, total_amount) VALUES (?, ?);",
            (invoice_number, grand_total)
        )
        invoice_id = cursor.lastrowid
        
        # Insert Invoice Items and Update stock levels
        for item in items:
            cursor.execute("SELECT price FROM products WHERE id = ?;", (item['id'],))
            current_price = cursor.fetchone()['price']
            item_subtotal = current_price * item['quantity']
            
            cursor.execute(
                """INSERT INTO invoice_items (invoice_id, product_id, quantity, price, subtotal)
                   VALUES (?, ?, ?, ?, ?);""",
                (invoice_id, item['id'], item['quantity'], current_price, item_subtotal)
            )
            
            # Decrease product stock
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?;",
                (item['quantity'], item['id'])
            )
            
        # Commit Transaction
        conn.commit()
        return jsonify({'success': True, 'invoice_id': invoice_id})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
