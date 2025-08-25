from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'bookstore.db'

app = Flask(__name__)
app.secret_key = 'dev_secret_key_change_this'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        price REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        cover_image TEXT
    );
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(book_id) REFERENCES books(id)
    );
    """)
    db.commit()

    # Insert default admin if not exists
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        hashed = generate_password_hash('adm123')
        cur.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                    ('admin', hashed, 'admin'))
        db.commit()

@app.route('/init')
def init():
    # Forceful database reset and re-population
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    # Re-initialize the database with the new, empty file
    init_db()
    
    db = get_db()
    cur = db.cursor()
    
    # Delete all books before re-inserting to ensure no duplicates
    cur.execute('DELETE FROM books')
    
    sample = [
        ('The Alchemist','Paulo Coelho',199.0,10, 'alchemist.jpg'),
        ('Clean Code','Robert C. Martin',499.0,5, 'clean_code.jpg'),
        ('Deep Learning','Ian Goodfellow',899.0,3, 'deep_learning.jpg'),
        ('Python Crash Course','Eric Matthes',299.0,7, 'python_crash_course.jpg'),
        ('Artificial Intelligence','Stuart Russell',799.0,4, 'ai.jpg'),
        ('Data Science Handbook','Jake VanderPlas',599.0,6, 'data_science_handbook.jpg'),
        ('Deep Learning with Python','François Chollet',699.0,5, 'dl_with_python.jpg'),
        ('The Pragmatic Programmer','Andrew Hunt',399.0,8, 'pragmatic_programmer.jpg'),
        ('Design Patterns','Erich Gamma',499.0,5, 'design_patterns.jpg'),
        ('Machine Learning Yearning','Andrew Ng',349.0,10, 'ml_yearning.jpg'),
        ('Fluent Python','Luciano Ramalho',649.0,6, 'fluent_python.jpg'),
        ('Introduction to Algorithms','Cormen et al.',899.0,4, 'intro_to_algorithms.jpg'),
        ('Python for Data Analysis','Wes McKinney',399.0,7, 'python_for_data_analysis.jpg'),
        ('Hands-On ML','Aurelien Geron',749.0,5, 'hands_on_ml.jpg'),
        ('Effective Java','Joshua Bloch',499.0,8, 'effective_java.jpg')
    ]
    cur.executemany('INSERT INTO books (title,author,price,stock,cover_image) VALUES (?,?,?,?,?)', sample)
    db.commit()

    return 'Database initialized with sample books and admin user. Go to /'

@app.route('/')
@app.route('/', methods=['GET', 'POST'])
def index():
    db = get_db()
    search_query = request.args.get('q', '')
    if search_query:
        books = db.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ?",
            (f"%{search_query}%", f"%{search_query}%")
        ).fetchall()
    else:
        books = db.execute('SELECT * FROM books').fetchall()
    
    # Fetch data for New Arrivals and Bestsellers sections
    new_arrivals = db.execute('SELECT * FROM books ORDER BY id DESC LIMIT 8').fetchall()
    bestsellers = db.execute('SELECT * FROM books ORDER BY stock ASC LIMIT 8').fetchall()

    # Define a list of colors to use for the card backgrounds
    card_colors = ['#FAD2E1', '#C6DBDA', '#F6C4C8', '#D8BFD8', '#B7E0E9', '#E0BBE4', '#95C5B9', '#FFD8A8']

    return render_template('index.html', books=books, new_arrivals=new_arrivals, bestsellers=bestsellers, search_query=search_query, card_colors=card_colors)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = generate_password_hash(password)
        db = get_db()
        try:
            db.execute('INSERT INTO users (username,password) VALUES (?,?)', (username, hashed))
            db.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except Exception:
            flash('Username taken or error.')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully.')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('index'))

@app.route('/add_to_cart/<int:book_id>')
def add_to_cart(book_id):
    if 'user_id' not in session:
        flash('Please login to add to cart.')
        return redirect(url_for('login'))
    user_id = session['user_id']
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id,quantity FROM cart WHERE user_id=? AND book_id=?', (user_id, book_id))
    row = cur.fetchone()
    if row:
        cur.execute('UPDATE cart SET quantity = quantity + 1 WHERE id=?', (row['id'],))
    else:
        cur.execute('INSERT INTO cart (user_id,book_id,quantity) VALUES (?,?,1)', (user_id, book_id))
    db.commit()
    flash('Added to cart.')
    return redirect(url_for('index'))

@app.route('/cart', methods=['GET','POST'])
def cart():
    if 'user_id' not in session:
        flash('Please login to view cart.')
        return redirect(url_for('login'))
    db = get_db()
    user_id = session['user_id']
    items = db.execute(
        'SELECT c.id, b.title, b.author, b.price, c.quantity, b.id as book_id FROM cart c JOIN books b ON c.book_id = b.id WHERE c.user_id=?',
        (user_id,)
    ).fetchall()
    total = sum([row['price']*row['quantity'] for row in items])
    return render_template('cart.html', items=items, total=total)

@app.route('/payment', methods=['GET','POST'])
def payment():
    if 'user_id' not in session:
        flash('Please login to proceed.')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']
    items = db.execute(
        'SELECT c.id, b.title, b.price, c.quantity, b.id as book_id FROM cart c JOIN books b ON c.book_id = b.id WHERE c.user_id=?',
        (user_id,)
    ).fetchall()
    total = sum([row['price']*row['quantity'] for row in items])

    if request.method == 'POST':
        cur = db.cursor()
        for item in items:
            stock = db.execute('SELECT stock FROM books WHERE id=?', (item['book_id'],)).fetchone()['stock']
            if item['quantity'] <= stock:
                cur.execute('UPDATE books SET stock = stock - ? WHERE id=?', (item['quantity'], item['book_id']))
        cur.execute('DELETE FROM cart WHERE user_id=?', (user_id,))
        db.commit()
        flash('Payment successful! Your order has been placed.')
        return redirect(url_for('index'))

    return render_template('payment.html', total=total, items=items)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if 'role' not in session or session.get('role') != 'admin':
        flash('Admin access only.')
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form.get('author','')
        price = float(request.form['price'] or 0)
        stock = int(request.form['stock'] or 0)
        # Added new form data for cover_image
        cover_image = request.form.get('cover_image', '')

        db.execute('INSERT INTO books (title,author,price,stock,cover_image) VALUES (?,?,?,?,?)', (title,author,price,stock,cover_image))
        db.commit()
        flash('Book added.')
    books = db.execute('SELECT * FROM books').fetchall()
    return render_template('admin.html', books=books)

@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    if 'role' not in session or session.get('role') != 'admin':
        flash('Admin access only.')
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM books WHERE id=?', (book_id,))
    db.commit()
    flash('Book deleted.')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
