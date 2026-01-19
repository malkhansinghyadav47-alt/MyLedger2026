import sqlite3

def init_db():
    # अगर यह जानकारी पहले से मौजूद है, तो इसे दोबारा मत डालो और चुपचाप आगे बढ़ जाओ
    #"""डेटाबेस और टेबल्स को इनिशियलाइज़ करें, साथ ही डिफ़ॉल्ट खाते डालें।"""
    with sqlite3.connect('business_ledger.db') as conn:
        cursor = conn.cursor()
        # अगर यह जानकारी पहले से मौजूद है, तो इसे दोबारा मत डालो और चुपचाप आगे बढ़ जाओ  
        # 1. Accounts Table (is_active के साथ)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                opening_bal REAL DEFAULT 0,
                phone TEXT,
                address TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # अगर यह जानकारी पहले से मौजूद है, तो इसे दोबारा मत डालो और चुपचाप आगे बढ़ जाओ
        # 2. Transactions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                date TEXT, 
                from_acc TEXT, 
                to_acc TEXT, 
                amount REAL, 
                note TEXT
            )
        ''')
        
        # 3. अपडेटेड डिफ़ॉल्ट खाते
        # यहाँ 'Plot Filling Expense' को बदलकर 'Construction Expense' कर दिया गया है
        defaults = [
            ('Cash', 0), ('Bank', 0), ('Sales Income', 0), 
            ('Personal Expense', 0), ('Office Expenses', 0), 
            ('Conveyance', 0), ('Miscellaneous', 0), 
            ('School Expenses', 0), ('Bills', 0),
            ('Salary Expense', 0), ('Construction Expense', 0)
        ]
        
        # अगर यह जानकारी पहले से मौजूद है, तो इसे दोबारा मत डालो और चुपचाप आगे बढ़ जाओ
        for name, bal in defaults:
            cursor.execute("""
                INSERT OR IGNORE INTO accounts (name, opening_bal, is_active) 
                VALUES (?, ?, 1)
            """, (name, bal))
            
        conn.commit()
        
def reset_database():
    """सावधानी: यह सभी ट्रांजेक्शन मिटा देगा!"""
    with sqlite3.connect('business_ledger.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
        conn.commit()
    print("Database Transactions Reset Successfully!")
    
# ऐप के स्टार्टअप पर इसे रन करें -> I've done in main application file
#init_db()