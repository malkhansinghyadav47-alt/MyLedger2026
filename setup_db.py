import sqlite3
# 1. Define the initialization logic
def init_db():
    with sqlite3.connect('business_ledger.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        opening_bal REAL DEFAULT 0,
                        phone TEXT,
                        address TEXT
                    )
                ''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                          (id INTEGER PRIMARY KEY, date TEXT, from_acc TEXT, to_acc TEXT, amount REAL, note TEXT)''')
        
        # Add default accounts if they don't exist
        defaults = [('Cash', 0), ('Bank', 0), ('Sales Income', 0), ('Personal Expense', 0)]
        for name, bal in defaults:
            cursor.execute("INSERT OR IGNORE INTO accounts (name, opening_bal) VALUES (?, ?)", (name, bal))
        conn.commit()
        
def reset_database():
    with sqlite3.connect('business_ledger.db') as conn:
        cursor = conn.cursor()
        # 1. Clear all transactions
        cursor.execute("DELETE FROM transactions")
        # 2. Reset the sequence counter for this table
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
        conn.commit()
    print("IDs have been reset to 1!")
    
# 2. RUN IT IMMEDIATELY
# init_db()