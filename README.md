# Bookstore Prototype (Flask)

Quick starter prototype for a simple bookstore web app.

## How to run
1. Make sure Python 3.8+ is installed.
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialize sample DB and data (or open /init in browser):
   ```bash
   python app.py
   ```
   Then visit http://127.0.0.1:5000/init once to load sample books.
5. Admin access: create a user in register, then open a Python shell and set role to admin:
   ```python
   import sqlite3
   conn = sqlite3.connect('bookstore.db')
   conn.execute("UPDATE users SET role='admin' WHERE username='your_admin_username'")
   conn.commit(); conn.close()
   ```
