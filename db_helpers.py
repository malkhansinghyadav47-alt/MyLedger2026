import re
import sqlite3
from datetime import date
from datetime import datetime

DB_NAME = "business_ledger.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# -------------------------------
# Financial Year Helpers
# -------------------------------

def get_active_financial_year():
    conn = get_connection()
    cur = conn.cursor()
    # 1. Fetch all needed columns
    cur.execute("SELECT id, label, start_date, end_date FROM financial_years WHERE is_active = 1")
    row = cur.fetchone()
    conn.close()

    if row:
        # 2. Return a dictionary so the calling code works
        return {
            "id": row[0],
            "label": row[1],
            "start_date": row[2],
            "end_date": row[3]
        }
    else:
        # 3. Return None instead of a string for cleaner logic
        return None

def get_all_financial_years():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, label, start_date, end_date, is_active
            FROM financial_years
            ORDER BY start_date DESC
        """)
        return cur.fetchall()


def set_active_financial_year(year_id):
    with get_connection() as conn:
        cur = conn.cursor()

        # deactivate all
        cur.execute("UPDATE financial_years SET is_active = 0")

        # activate selected
        cur.execute("""
            UPDATE financial_years 
            SET is_active = 1 
            WHERE id = ?
        """, (year_id,))

        conn.commit()
        
# -------------------------------
# Financial Year CRUD Helpers
# -------------------------------

def generate_fy_dates(label):
    """
    Converts '2026-27' → ('2026-04-01', '2027-03-31')
    Enforces:
    - Format YYYY-YY
    - Year between 2000 and 2099
    """

    pattern = r"^(\d{4})-(\d{2})$"
    match = re.match(pattern, label.strip())

    if not match:
        raise ValueError("Invalid format. Use YYYY-YY (e.g. 2026-27)")

    start_year = int(match.group(1))
    end_year_suffix = int(match.group(2))

    # 🔒 Century bound check
    if start_year < 2000 or start_year > 2099:
        raise ValueError("Financial year must be between 2000-01 and 2099-00")

    # 🔒 Logical FY continuity check
    if (start_year + 1) % 100 != end_year_suffix:
        raise ValueError("Invalid financial year sequence (e.g. 2026-27)")

    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)

    return start_date.isoformat(), end_date.isoformat()

def add_financial_year(label):
    try:
        start_date, end_date = generate_fy_dates(label)

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO financial_years (label, start_date, end_date, is_active)
                VALUES (?, ?, ?, 0)
            """, (label.strip(), start_date, end_date))
            conn.commit()

        return True, ""

    except ValueError as ve:
        return False, str(ve)

    except sqlite3.IntegrityError:
        return False, f"Financial Year '{label}' already exists"


def update_financial_year(year_id, label):

    label = label.strip()
    start_date, end_date = generate_fy_dates(label)

    with get_connection() as conn:
        cur = conn.cursor()

        # 🔒 Check duplicate label EXCEPT current record
        cur.execute("""
            SELECT id 
            FROM financial_years 
            WHERE label = ? AND id != ?
        """, (label, year_id))

        if cur.fetchone():
            raise ValueError(f"Financial Year '{label}' already exists")

        # ✅ Safe update
        cur.execute("""
            UPDATE financial_years
            SET label = ?, start_date = ?, end_date = ?
            WHERE id = ?
        """, (label, start_date, end_date, year_id))

        conn.commit()

def can_delete_financial_year(year_id):
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM opening_balances WHERE financial_year_id = ?",
            (year_id,)
        )
        if cur.fetchone()[0] > 0:
            return False

        cur.execute(
            "SELECT COUNT(*) FROM transactions WHERE financial_year_id = ?",
            (year_id,)
        )
        if cur.fetchone()[0] > 0:
            return False

        return True


def delete_financial_year(year_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM financial_years WHERE id = ?", (year_id,))
        conn.commit()

        
# -------------------------------
# Groups Helpers
# -------------------------------

def add_group(group_name):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO groups (group_name) VALUES (?)",
            (group_name.strip(),)
        )
        conn.commit()


def get_all_groups():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, group_name FROM groups ORDER BY group_name")
        return cur.fetchall()

def update_group(group_id, new_name):
    new_name = new_name.strip()

    if not new_name:
        raise ValueError("Group name cannot be empty")

    with get_connection() as conn:
        cur = conn.cursor()

        # Duplicate check
        cur.execute("""
            SELECT id FROM groups
            WHERE group_name = ? AND id != ?
        """, (new_name, group_id))

        if cur.fetchone():
            raise ValueError("Group already exists")

        cur.execute("""
            UPDATE groups
            SET group_name = ?
            WHERE id = ?
        """, (new_name, group_id))

        conn.commit()

def can_delete_group(group_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM accounts WHERE group_id = ?",
            (group_id,)
        )
        return cur.fetchone()[0] == 0

def delete_group(group_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        conn.commit()


# -------------------------------
# ACCOUNTS HELPERS
# -------------------------------

import sqlite3

def get_all_groups():
    with get_connection() as conn:
        # This ensures row['column'] works, but we'll go one step further
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()
        cur.execute("SELECT id, group_name FROM groups ORDER BY group_name")
        rows = cur.fetchall()
        # Convert to true dictionaries so .get() works in Streamlit
        return [dict(row) for row in rows]

def get_all_accounts():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.id, a.name, a.phone, a.address, 
                a.is_active, a.group_id, g.group_name
            FROM accounts a
            JOIN groups g ON a.group_id = g.id
            ORDER BY a.name
        """)
        rows = cur.fetchall()
        return [dict(row) for row in rows]

def add_account(name, group_id, phone="", address=""):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO accounts (name, group_id, phone, address)
            VALUES (?, ?, ?, ?)
        """, (name.strip(), group_id, phone.strip(), address.strip()))
        conn.commit()


def update_account(account_id, name, phone="", address="", group_id=None):
    name = name.strip()
    if not name:
        raise ValueError("Account name cannot be empty")

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM accounts
            WHERE name = ? AND id != ?
        """, (name, account_id))

        if cur.fetchone():
            raise ValueError("Account name already exists")

        cur.execute("""
            UPDATE accounts
            SET name = ?, phone = ?, address = ?, group_id = ?
            WHERE id = ?
        """, (name, phone, address, group_id, account_id))

        conn.commit()

def deactivate_account(account_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE accounts
            SET is_active = 0
            WHERE id = ?
        """, (account_id,))
        conn.commit()

def get_groups_for_dropdown():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, group_name FROM groups ORDER BY group_name")
        return cur.fetchall()

def toggle_account_status(account_id, is_active):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE accounts
        SET is_active = ?
        WHERE id = ?
    """, (is_active, account_id))

    conn.commit()
    conn.close()
        
        
# -------------------------------
# OPENING BALANCE HELPERS
# -------------------------------

def get_all_accounts_simple():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM accounts WHERE is_active = 1 ORDER BY name")
        return cur.fetchall()


def add_opening_balance(account_id, financial_year_id, amount):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO opening_balances 
            (account_id, financial_year_id, amount)
            VALUES (?, ?, ?)
        """, (account_id, financial_year_id, amount))
        conn.commit()


def get_opening_balances(financial_year_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.name, ob.amount
            FROM opening_balances ob
            JOIN accounts a ON ob.account_id = a.id
            WHERE ob.financial_year_id = ?
            ORDER BY a.name
        """, (financial_year_id,))
        return cur.fetchall()


# ---------------------------------
# TRANSACTIONS HELPERS
# ---------------------------------

def add_transaction(txn_date, from_acc_id, to_acc_id, amount, note, financial_year_id, created_by):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions 
        (txn_date, from_acc_id, to_acc_id, amount, note, financial_year_id, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        txn_date,
        from_acc_id,
        to_acc_id,
        amount,
        note,
        financial_year_id,
        created_by,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

def get_transactions_by_year(financial_year_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            t.id,
            t.txn_date,
            a1.name AS from_account,
            a2.name AS to_account,
            t.amount,
            t.note
        FROM transactions t
        JOIN accounts a1 ON t.from_acc_id = a1.id
        JOIN accounts a2 ON t.to_acc_id = a2.id
        WHERE t.financial_year_id = ?
        ORDER BY t.txn_date DESC, t.id DESC
    """, (financial_year_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

# -------------------------------
# Date Helpers
# ------------------------------

def indian_date(date_str):
    # DB format YYYY-MM-DD  →  DD-MM-YYYY
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")

