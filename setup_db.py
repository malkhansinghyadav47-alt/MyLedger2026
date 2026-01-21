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
                phone TEXT,
                group_type TEXT,
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opening_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                balance REAL,
                type TEXT,              -- 'Debit' or 'Credit'
                financial_year TEXT    -- '2024-25 etc'
            )
        ''')       
        
        # 3. अपडेटेड डिफ़ॉल्ट खाते
        # यहाँ 'Plot Filling Expense' को बदलकर 'Construction Expense' कर दिया गया है
        defaults = [
            'Cash', 'Bank', 'Sales Income', 'Personal Expense',
            'Office Expenses', 'Conveyance', 'Miscellaneous',
            'School Expenses', 'Bills', 'Salary Expense', 'Construction Expense'
        ]

        for name in defaults:
            cursor.execute("""
                INSERT OR IGNORE INTO accounts (name, is_active, group_type) 
                VALUES (?, 1, 'Party')
            """, (name,))
           
        conn.commit()
       
# इसे सिर्फ एक बार रन करना है ताकि टेबल अपडेट हो जाए
def upgrade_database():
    conn = sqlite3.connect("business_ledger.db") # अपने DB का नाम लिखें
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE accounts ADD COLUMN group_type TEXT DEFAULT 'Party'")
        conn.commit()
        print("✅ Database updated successfully!")
    except Exception as e:
        print(f"Note: {e}") # अगर कॉलम पहले से है तो एरर आएगा जिसे इग्नोर कर सकते हैं
    finally:
        conn.close()
         
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