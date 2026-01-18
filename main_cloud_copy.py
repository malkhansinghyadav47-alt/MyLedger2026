import streamlit as st
import io
import urllib.parse
import sqlite3
import pandas as pd
from fpdf import FPDF
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go
import urllib.parse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import difflib # Ensure this is at the top of your file
from difflib import SequenceMatcher
from setup_db import init_db, reset_database

# Initialize the database by running the setup script from setup_db.py
init_db()
# reset_database()

# --- CLEAN DATABASE HELPERS ---
DB_FILE = 'business_ledger.db'

def get_query(query, params=()):
    """Use this for all SELECT statements"""
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(query, conn, params=params)

def run_action(query, params=()):
    """Use this for all INSERT, UPDATE, DELETE statements"""
    with sqlite3.connect(DB_FILE) as conn:
        curr = conn.cursor()
        curr.execute(query, params)
        conn.commit()

try:
    # This adds the column if it doesn't exist. DEFAULT 1 keeps everyone active.
    run_action("ALTER TABLE accounts ADD COLUMN is_active INTEGER DEFAULT 1")
except Exception:
    pass # Column already exists

# Alias for compatibility if your dashboard uses 'run_query'
def run_query(query, params=()):
    return get_query(query, params)

# --- INITIALIZATION (Ensure these are at the top of your script) ---
if 'should_reset' not in st.session_state:
    st.session_state['should_reset'] = False
if 'confirm_delete' not in st.session_state:
    st.session_state['confirm_delete'] = False

def trigger_reset():
    """Callback to signal a reset in the next run"""
    st.session_state['should_reset'] = True
    st.session_state['confirm_delete'] = False
        
def fmt_date(d):
    return d.strftime("%d-%m-%Y")

pdfmetrics.registerFont(
    TTFont("Noto", "fonts/NotoSans-Regular.ttf")
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_directory_pdf(df):
    buffer = BytesIO()
    # Create the canvas
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- Header ---
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, "PARTY DIRECTORY REPORT")
    
    y -= 30
    c.setFont("Noto", 10) # Using Noto as your other working code does
    c.drawCentredString(width/2, y, f"Total Records: {len(df)}")
    c.line(40, y-10, width-40, y-10)

    # --- Table Headers ---
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "ID")
    c.drawString(80, y, "Name")
    c.drawString(240, y, "Phone")
    c.drawString(360, y, "Address")
    
    # --- Data Rows ---
    y -= 20
    c.setFont("Noto", 9)
    
    for _, row in df.iterrows():
        if y < 50: # Check for new page
            c.showPage()
            y = height - 50
            c.setFont("Noto", 9)

        # CLEAN THE TEXT: Convert to string and handle None/Null values
        # This prevents the "NoneType" error you saw earlier
        p_id = str(row['id'])
        p_name = str(row['name'] if row['name'] else "")
        p_phone = str(row['phone'] if row['phone'] else "")
        p_addr = str(row['address'] if row['address'] else "")

        try:
            c.drawString(50, y, p_id)
            c.drawString(80, y, p_name[:40]) # Truncate if too long
            c.drawString(240, y, p_phone)
            c.drawString(360, y, p_addr[:45])
        except:
            # If Noto fails on a specific character, fallback to Helvetica
            c.setFont("Helvetica", 9)
            c.drawString(80, y, "Text encoding error in this row")
            c.setFont("Noto", 9)
            
        y -= 20

    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def generate_pdf(book, start_date, end_date, df, money_in, money_out, net_bal, msg_hindi):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, "ACCOUNT STATEMENT")

    y -= 25
    c.setFont("Noto", 12)
    c.drawCentredString(width/2, y, book)

    y -= 20
    c.drawCentredString(width/2, y, f"Period: {fmt_date(start_date)} to {fmt_date(end_date)}")

    y -= 30
    c.line(40, y, width-40, y)

    y -= 25
    c.drawString(50, y, f"Total In : ₹{money_in:,.2f}")
    y -= 20
    c.drawString(50, y, f"Total Out: ₹{money_out:,.2f}")
    y -= 20
    c.drawString(50, y, f"Net Balance: ₹{net_bal:,.2f}")

    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Date")
    c.drawString(120, y, "From")
    c.drawString(240, y, "To")
    c.drawString(350, y, "Amount")

    c.setFont("Noto", 10)
    y -= 15

    for _, row in df.iterrows():
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, fmt_date(row['date']))
        c.drawString(120, y, row['from_acc'])
        c.drawString(240, y, row['to_acc'])
        c.drawRightString(430, y, f"₹{row['amount']:,.2f}")
        y -= 15

    y -= 20
    c.setFont("Noto", 9)
    c.drawCentredString(width/2, y, msg_hindi)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def save_and_reset():
    # 1. Access the data currently in the widgets
    # We use .get() to avoid errors if the key is missing
    f = st.session_state.get("sb_f_acc")
    t = st.session_state.get("sb_t_acc")
    a = st.session_state.get("sb_amt", 0.0)
    n = st.session_state.get("sb_note", "")
    d = st.session_state.get("sb_date", datetime.now())

    # 2. Save to Database
    run_action("INSERT INTO transactions (date, from_acc, to_acc, amount, note) VALUES (?,?,?,?,?)",
               (d.strftime("%Y-%m-%d"), f, t, a, n))

# 3. FORCE INITIALIZATION (The Update)
    # Instead of deleting, we set them back to their default values
    st.session_state["sb_f_acc"] = "-- Select Account --"
    st.session_state["sb_t_acc"] = "-- Select Account --"
    st.session_state["sb_amt"] = 0.0
    st.session_state["sb_note"] = ""
            
    st.toast(f"✅ Saved ₹{a} Successfully!")

# --- 1. SETTINGS & SECURITY ---
st.set_page_config(page_title="Ledger 2026", layout="wide", page_icon="📈")

# Simple Password Protection
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("📖 JGMPS Ledger")
        st.title("🔐 Secure Login")
        pwd = st.text_input("Enter Business Key", type="password")
        if st.button("Unlock Ledger"):
            if pwd == "1234": # <--- CHANGE YOUR PASSWORD HERE
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong Key!")
        return False
    return True

# --- 3. MAIN APP ---
if check_password():
    st.title("📊 Jan Gan Man Public School Ledger 2026 Dashboard")
    
    # CALCULATE TOTALS
    acc_df = run_query("SELECT * FROM accounts")
    trans_df = run_query("SELECT * FROM transactions")
    
    # Business Metrics (Top Row)
    c1, c2, c3, c4, c5 = st.columns(5) # Added 5th column
    
    def get_bal(name):
        inflow = trans_df[trans_df['to_acc'] == name]['amount'].sum()
        outflow = trans_df[trans_df['from_acc'] == name]['amount'].sum()
        open_bal = acc_df[acc_df['name'] == name]['opening_bal'].values[0] if name in acc_df['name'].values else 0
        return open_bal + inflow - outflow

    cash = get_bal("Cash")
    bank = get_bal("Bank")
    sales = trans_df[trans_df['to_acc'] == 'Sales Income']['amount'].sum()
    expenses = trans_df[trans_df['to_acc'] == 'Personal Expense']['amount'].sum()
    
    # NEW MATH: Profit calculation
    # --- Calculation Logic ---
    # Sales: Sum of amount where 'from_acc' is 'Sales Income'
    sales = trans_df[trans_df['from_acc'] == 'Sales Income']['amount'].sum()

    # Expenses: Sum of amount where 'to_acc' is 'Personal Expense'
    expenses = trans_df[trans_df['to_acc'] == 'Personal Expense']['amount'].sum()

    # Profit Math
    profit = sales - expenses
    # Calculate Margin %
    margin_pct = (profit / sales * 100) if sales > 0 else 0
    
    # UI: 5 Columns for 5 Cards
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("💵 Cash in Hand", f"₹{cash:,.2f}")
    c2.metric("🏦 Bank Balance", f"₹{bank:,.2f}")
    c3.metric("📈 Total Sales", f"₹{sales:,.2f}")
    c4.metric("📉 Total Expenses", f"₹{expenses:,.2f}", delta_color="inverse")
    c5.metric("🎯 Margin %", f"{margin_pct:.1f}%", delta=f"{margin_pct:.1f}%")
    
    # NEW METRIC: Profit Display
    # This will turn green if positive, red if negative
    # Change this line:
    c5.metric("💰 Net Profit", f"₹{profit:,.2f}", delta=f"{profit:,.2f}")
    
    st.divider()
   
    # D. ANALYTICS SECTION (The "Graphs Card")
    with st.expander("📊 VIEW BUSINESS ANALYTICS & CHARTS", expanded=False):
        if not trans_df.empty:
            view = st.radio("Graph Scale:", ["Daily", "Monthly"], horizontal=True, key="graph_toggle")
            
            # Prepare Plot Data
            chart_df = trans_df.copy()
            chart_df['date'] = pd.to_datetime(chart_df['date'])
            chart_df['period'] = chart_df['date'].dt.date if view == "Daily" else chart_df['date'].dt.strftime('%b %Y')
            
            trends = chart_df.groupby(['period', 'to_acc'])['amount'].sum().reset_index()
            core_accs = ['Cash', 'Bank', 'Sales Income', 'Personal Expense']
            plot_df = trends[trends['to_acc'].isin(core_accs)]

            col_chart, col_gauge = st.columns([2, 1])
            
            with col_chart:
                fig_line = px.line(plot_df, x='period', y='amount', color='to_acc', markers=True,
                                   title=f"{view} Trend Analysis", template="plotly_dark",
                                   color_discrete_map={"Sales Income": "#00FF00", "Personal Expense": "#FF4B4B"})
                st.plotly_chart(fig_line, use_container_width=True)

            with col_gauge:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number", value=margin_pct,
                    number={'suffix': "%"}, title={'text': "Profit Margin"},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#00FF00" if margin_pct > 30 else "#FFA500"}}
                ))
                fig_gauge.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10), template="plotly_dark")
                st.plotly_chart(fig_gauge, use_container_width=True)

            st.divider()
            # Bar Chart Comparison
            comp_df = pd.DataFrame({"Category": ["Sales", "Expenses"], "Amount": [sales, expenses]})
            fig_bar = px.bar(comp_df, x="Category", y="Amount", color="Category", text_auto='.2s',
                             title="Revenue vs Expenditure", template="plotly_dark",
                             color_discrete_map={"Sales": "#00FF00", "Expenses": "#FF4B4B"})
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No data available to generate graphs.")
                        
    # --- 2. THE SIDEBAR UI ---
    with st.sidebar:
        # GUIDELINE BOX FOR USER
        st.info("""**📖 JGMPS**
        - **Quick Guide:**
        - **Sales:** Paid By: `Sales Income` → Received By: `Cash/Bank`
        - **Expense:** Paid By: `Cash/Bank` → Received By: `Personal Expense`
        - **Deposit:** Paid By: `Cash` → Received By: `Bank`""")
                
        st.header("➕ Add New Transaction")
        t_date = st.date_input("Date", datetime.now(), key="sb_date")

        # 1. Get the full list from DB
        active_parties_df = get_query("SELECT name FROM accounts WHERE is_active = 1 ORDER BY name ASC")
        names = active_parties_df['name'].tolist()
        
        if not names:
            st.warning("No active parties found. Please activate or add a party in the Directory.")
        else:
            # 2. Add a "Placeholder" at index 0
            options_with_null = ["-- Select Account --"] + names

            # 3. Filter the lists
            source_options = [n for n in options_with_null if n != "Personal Expense"]
            dest_options = [n for n in options_with_null if n != "Sales Income"]

            # 4. The Selectboxes
            f_acc = st.selectbox("Paid By (Source)", source_options, index=0, key="sb_f_acc")
            t_acc = st.selectbox("Received By (Destination)", dest_options, index=0, key="sb_t_acc")

            amt = st.number_input("Amount (INR)", min_value=0.0, step=100.0, key="sb_amt")
            note = st.text_input("Remark", key="sb_note")

            # --- CLEANED VALIDATION LOGIC ---
            is_valid = True

            # Rule 1: Check placeholders
            if f_acc == "-- Select Account --" or t_acc == "-- Select Account --":
                st.info("💡 Please select both Source and Destination.")
                is_valid = False
            
            # Rule 2: Cannot be the same
            elif f_acc == t_acc:
                st.error("❌ Source and Destination cannot be the same.")
                is_valid = False
                
            # Rule 3: Check for amount
            if amt <= 0:
                is_valid = False

            # --- SAVE BUTTON WITH CALLBACK ---
            # We use on_click to run the save_and_reset function
            st.button(
                "💾 Save to Ledger", 
                on_click=save_and_reset, 
                disabled=not is_valid, 
                use_container_width=True,
                key="save_btn"
            )
        
        st.divider()
        with st.expander("👥 Adding Parties", expanded=False):
            # --- ADD NEW PARTY SECTION ---
            st.header("📋 Add New Party")

            # 1. Fetch existing data for warning purposes
            try:
                existing_df = get_query("SELECT name, phone FROM accounts")
                existing_names = existing_df['name'].tolist() if not existing_df.empty else []
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                existing_names = []

            # 2. SEPARATE INPUT ROWS
            new_p_raw = st.text_input("1️⃣ Party Name", placeholder="e.g., Rahul Kumar", key="p_name")
            new_phone = st.text_input("2️⃣ Phone Number", placeholder="e.g., 9876543210", key="p_phone")
            new_address = st.text_area("3️⃣ Full Address", placeholder="Location details...", key="p_addr", height=100)

            # --- WARNING LOGIC (Not Prevention) ---
            new_p_clean = new_p_raw.strip()
            is_duplicate = False

            if new_p_clean:
                # Check for exact matches
                exact_matches = [n for n in existing_names if n.lower() == new_p_clean.lower()]
                
                if exact_matches:
                    is_duplicate = True
                    st.warning(f"⚠️ **Note:** There is already a person named **'{new_p_clean}'** in your list.")
                    st.info("If this is a different person with the same name, you can still proceed by checking the box below.")
                else:
                    # Check for fuzzy/similar matches
                    close_matches = difflib.get_close_matches(new_p_clean.lower(), [n.lower() for n in existing_names], n=2, cutoff=0.7)
                    if close_matches:
                        is_duplicate = True
                        st.info(f"💡 Similar names found: {', '.join(close_matches)}. Ensure this isn't a typo.")

            # 3. THE "PROCEED ANYWAY" CHECKBOX
            # This appears only if a duplicate/similar name is found
            confirm_add = True
            if is_duplicate:
                confirm_add = st.checkbox("Yes, this is a different person. Add them anyway.", key="force_add")

            # 4. ACTION BUTTON
            # Enabled if name is typed AND (it's not a duplicate OR user checked the box)
            if st.button("➕ Register New Party", use_container_width=True, disabled=not (new_p_clean and confirm_add)):
                try:
                    run_action(
                        "INSERT INTO accounts (name, opening_bal, phone, address) VALUES (?, 0, ?, ?)",
                        (new_p_clean, new_phone.strip(), new_address.strip())
                    )
                    st.success(f"✅ Registered '{new_p_clean}' successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"🚫 Database error: {e}")
                
        # --- PARTY DIRECTORY SECTION ---
        with st.expander("View, Edit, Delete or Download Parties 📋", expanded=False):
            st.subheader("Master List")

            # 1. Fetch data
            directory_df = get_query("SELECT id, name, phone, address, is_active FROM accounts")
            
            if not directory_df.empty:
                # --- PART A: DISPLAY LIST ---
                col1, col2 = st.columns([2, 1])
                with col1:
                    search_query = st.text_input("🔍 Search list...", placeholder="Type name or phone...", key="dir_search")
                with col2:
                    # Filter to toggle between seeing only Active or All parties
                    filter_status = st.selectbox("Show Status", ["Active Only", "All Records"])

                view_df = directory_df.copy()

                # Filter 1: By Status (Active vs Hidden)
                if filter_status == "Active Only":
                    view_df = view_df[view_df['is_active'] == 1]

                # Filter 2: By Search Query
                if search_query:
                    view_df = view_df[
                        view_df['name'].str.contains(search_query, case=False, na=False) |
                        view_df['phone'].str.contains(search_query, case=False, na=False)
                    ]

                # --- VISUAL FIX: Replace 1/0 with Emojis for the Table ---
                # We create a display version so the underlying data stays clean for CSV/PDF
                display_df = view_df.copy()
                display_df['is_active'] = display_df['is_active'].apply(lambda x: "✅ Active" if x == 1 else "❌ Hidden")
                
                # Rename column for better looks
                display_df.columns = ['ID', 'Name', 'Phone', 'Address', 'Status']

                st.dataframe(
                    display_df[['ID', 'Status', 'Name', 'Phone', 'Address']], 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # --- 4. Report Download Options ---
                st.divider()
                st.subheader("📥 Export Directory")

                col_csv, col_pdf = st.columns(2)

                with col_csv:
                    csv = view_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name="party_directory.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with col_pdf:
                    # Logic to generate and provide the PDF
                    pdf_bytes = generate_directory_pdf(view_df)
                    if pdf_bytes:
                        st.download_button(
                            label="📑 Download PDF",
                            data=pdf_bytes,
                            file_name="party_directory.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="dir_pdf_download" # Unique key is important
                        )
                        
                    else:
                        st.error("Failed to build PDF. Ensure no unusual symbols are in the text.")
                       
                st.divider()

                # --- PART B: EDIT SECTION ---
                st.subheader("✏️ Edit Party Details")

                # 1. Fetch ALL records for the editor
                full_directory_df = get_query("SELECT id, name, phone, address, is_active FROM accounts")

                # 2. Add a filter specifically for the Edit dropdown
                edit_view_filter = st.radio(
                    "Filter list for editing:", 
                    ["Show All", "Active Only", "Inactive Only"], 
                    horizontal=True,
                    key="edit_view_toggle"
                )

                # 3. Apply the filter to the dropdown list
                if edit_view_filter == "Active Only":
                    filtered_edit_df = full_directory_df[full_directory_df['is_active'] == 1]
                elif edit_view_filter == "Inactive Only":
                    filtered_edit_df = full_directory_df[full_directory_df['is_active'] == 0]
                else:
                    filtered_edit_df = full_directory_df

                # 4. Create labels for the selectbox
                party_options = filtered_edit_df.apply(
                    lambda x: f"{'✅' if x['is_active']==1 else '❌'} {x['name']} | ID: {x['id']}", 
                    axis=1
                ).tolist()

                selected_party_label = st.selectbox(
                    "Select a Party to Update", 
                    ["-- Choose --"] + party_options, 
                    key="editor_select"
                )

                if selected_party_label != "-- Choose --":
                    # Extract ID from the label
                    selected_id = int(selected_party_label.split("ID: ")[1])
                    current_person = full_directory_df[full_directory_df['id'] == selected_id].iloc[0]
    
                    with st.form("edit_form"):
                        val_name = current_person['name'] if current_person['name'] else ""
                        val_phone = current_person['phone'] if current_person['phone'] else ""
                        val_addr = current_person['address'] if current_person['address'] else ""       
                        
                        updated_name = st.text_input("Edit Name", value=val_name)
                        updated_phone = st.text_input("Edit Phone Number", value=val_phone)
                        updated_addr = st.text_area("Edit Address", value=val_addr, height=100)
                        
                        # --- Toggle for Hiding (Soft Delete) ---
                        is_active = st.toggle(
                            "✅ Show in active lists?", 
                            value=(current_person['is_active'] == 1), 
                            help="Turn off to hide this party from transaction lists without deleting their history."
                        )
                        
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
                            clean_name = str(updated_name).strip() if updated_name else ""
                            clean_phone = str(updated_phone).strip() if updated_phone else ""
                            clean_addr = str(updated_addr).strip() if updated_addr else ""
                            status_val = 1 if is_active else 0

                            try:
                                run_action(
                                    "UPDATE accounts SET name=?, phone=?, address=?, is_active=? WHERE id=?",
                                    (clean_name, clean_phone, clean_addr, status_val, selected_id)
                                )
                                st.success(f"✅ Changes for '{clean_name}' saved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"🚫 Error updating: {e}")

                    # --- PART C: PERMANENT DELETE (Outside Form for Safety) ---
                    st.write("---")
                    with st.expander("🗑️ Danger Zone (Permanent Delete)"):
                        st.warning(f"Are you sure you want to delete **{current_person['name']}** forever?")
                        if st.button(f"Confirm Permanent Delete: {current_person['name']}", type="primary", use_container_width=True):
                            # SAFETY CHECK: Check if transactions exist
                            check_trans = get_query(
                                "SELECT COUNT(*) as total FROM transactions WHERE from_acc=? OR to_acc=?", 
                                (current_person['name'], current_person['name'])
                            )
                            
                            if check_trans['total'][0] > 0:
                                st.error(f"❌ Cannot Delete! This party has {check_trans['total'][0]} transactions. Please use the 'Active' toggle above to hide them instead.")
                            else:
                                run_action("DELETE FROM accounts WHERE id=?", (selected_id,))
                                st.success("Record deleted permanently.")
                                st.rerun()
                                
            else:
                st.info("No parties registered yet.")
                                               
        # --- MAIN AREA: TABS (Updated with Books) ---
    tab1, tab2, tab3, tab4 = st.tabs(["📜 Recent History", "📖 Books", "🔍 Advanced Search", "📂 Export & Tools"])
    with tab1:
        st.subheader("Full Transaction History")
        
        # 1. Reverse the data so newest is on top
        full_history = trans_df.iloc[::-1].copy()
        
        # 2. Define a function to color the rows
        # This highlights 'Personal Expense' in light red
        def highlight_expenses(row):
            color = 'background-color: #ffcccc; color: black' if row.to_acc == 'Personal Expense' else ''
            return [color] * len(row)

        # 3. Apply the styling and show ALL data
        # We use .style to make it look professional
        st.dataframe(
            full_history.style.apply(highlight_expenses, axis=1), 
            use_container_width=True,
            height=400 # Adds a scrollbar after this height
        )
        
        st.caption("💡 Red rows indicate Personal Expenses")
        st.caption("Courtesy of Jan Gan Man Public School Muradnagar")

    with tab2:
            st.subheader("📖 Account Statements (Books)")
            all_accs = acc_df['name'].tolist()
            
            # 1. SELECT PARTY AND DATES
            col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
            with col_s1:
                selected_book = st.selectbox("Select Book to View", all_accs, key="book_selector")
            with col_s2:
                start_date = st.date_input("From", datetime(2026, 1, 1), key="book_start")
            with col_s3:
                end_date = st.date_input("To", datetime.now(), key="book_end")
            
            # 2. FILTER DATA BY PARTY AND DATE RANGE
            book_df = trans_df[(trans_df['from_acc'] == selected_book) | (trans_df['to_acc'] == selected_book)].copy()
            book_df['date'] = pd.to_datetime(book_df['date']).dt.date
            
            # Apply the date filter
            mask = (book_df['date'] >= start_date) & (book_df['date'] <= end_date)
            filtered_df = book_df.loc[mask]
            
            if not filtered_df.empty:
                st.write(f"Statement for **{selected_book}** from {fmt_date(start_date)} to {fmt_date(end_date)}")
                st.dataframe(filtered_df, use_container_width=True)
                                
                # --- TAB 2: ACTION UI ---
                st.markdown("### 🛠️ Record Actions")

                # --- THE RESET GUARD ---
                # This runs BEFORE the widget is created, making it safe to modify the state
                if st.session_state.get('should_reset', False):
                    st.session_state['action_id_input'] = 0
                    st.session_state['should_reset'] = False 

                action_col1, action_col2 = st.columns(2)

                with action_col1:
                    edit_id = st.number_input(
                        "Enter ID to Edit/Delete", 
                        min_value=0, 
                        step=1, 
                        key="action_id_input"
                    )

                if edit_id > 0:
                    # Fetch the specific record
                    target_row = filtered_df[filtered_df['id'] == edit_id] if not filtered_df.empty else pd.DataFrame()

                    if not target_row.empty:
                        col_btn1, col_btn2 = st.columns(2)
                        
                        # 1. DELETE LOGIC WITH CONFIRMATION
                        if col_btn1.button("🗑️ Request Delete", use_container_width=True, key="req_del_btn"):
                            st.session_state['confirm_delete'] = True

                        if st.session_state.get('confirm_delete', False):
                            with st.status("⚠️ Confirm Deletion", expanded=True):
                                st.write(f"Are you sure you want to permanently delete Record ID: {edit_id}?")
                                c1, c2 = st.columns(2)
                                if c1.button("✅ Yes, Delete", type="primary", use_container_width=True):
                                    run_action("DELETE FROM transactions WHERE id=?", (int(edit_id),))
                                    st.session_state['should_reset'] = True  # Signal reset
                                    st.success(f"Record {edit_id} deleted.")
                                    st.rerun()
                                
                                # Use the callback for the 'No' button
                                c2.button("❌ No, Keep it", use_container_width=True, on_click=trigger_reset)

                        # 2. EDIT LOGIC (Expandable Form)
                        with st.expander("📝 Edit Details", expanded=True):
                            # Store original values for comparison
                            orig_date = pd.to_datetime(target_row['date'].values[0]).date()
                            orig_from = target_row['from_acc'].values[0]
                            orig_to = target_row['to_acc'].values[0]
                            orig_amt = float(target_row['amount'].values[0])
                            orig_note = target_row['note'].values[0]

                            # Widgets
                            new_date = st.date_input("New Date", value=orig_date)
                            new_from = st.selectbox("New Paid By", all_accs, index=all_accs.index(orig_from))
                            new_to = st.selectbox("New Received By", all_accs, index=all_accs.index(orig_to))
                            new_amt = st.number_input("New Amount", value=orig_amt)
                            new_note = st.text_input("New Remark", value=orig_note)

                            # Change Detection
                            has_changed = (
                                new_date != orig_date or new_from != orig_from or 
                                new_to != orig_to or new_amt != orig_amt or new_note != orig_note
                            )

                            eb1, eb2 = st.columns(2)
                            with eb1:
                                if st.button("💾 Save Changes", type="primary", use_container_width=True, disabled=not has_changed):
                                    run_action("""UPDATE transactions SET date=?, from_acc=?, to_acc=?, amount=?, note=? WHERE id=?""", 
                                            (new_date.strftime("%Y-%m-%d"), new_from, new_to, new_amt, new_note, int(edit_id)))
                                    st.session_state['should_reset'] = True  # Signal reset
                                    st.success("Record Updated!")
                                    st.rerun()
                            
                            with eb2:
                                # Use the callback to avoid "instantiated" error
                                st.button("❌ Cancel Edit", use_container_width=True, on_click=trigger_reset)
                            
                            if not has_changed:
                                st.caption("ℹ️ Modify a field to enable the Save button.")

                    else:
                        st.error(f"ID {edit_id} not found in this book.")
                else:
                    st.caption("Select a record ID from the table above to Edit or Delete.")
                                                
                # 3. CALCULATE TOTALS FOR SELECTED PERIOD
                money_in = filtered_df[filtered_df['to_acc'] == selected_book]['amount'].sum()
                money_out = filtered_df[filtered_df['from_acc'] == selected_book]['amount'].sum()
                net_bal = money_in - money_out

                if net_bal > 0:
                    bal_label = "Owes You (उसको देने हैं)"
                    msg_hindi = f"आपकी तरफ मेरा हिसाब ({fmt_date(start_date)} से {fmt_date(end_date)}) ₹{net_bal:,.2f} है जो आप मुझे देंगे।"
                    delta_color = "normal"
                elif net_bal < 0:
                    bal_label = "You Owe (आपको देने हैं)"
                    msg_hindi = f"मेरी तरफ आपका हिसाब ({fmt_date(start_date)} से {fmt_date(end_date)}) ₹{abs(net_bal):,.2f} है जो मैं आपको दूंगा।"
                    delta_color = "inverse"
                else:
                    bal_label = "Settled (बराबर)"
                    msg_hindi = f"{fmt_date(start_date)} से {fmt_date(end_date)} का हिसाब बराबर है।"
                    delta_color = "off"
                
                bc1, bc2, bc3 = st.columns(3)
                bc1.metric("Total In", f"₹{money_in:,.2f}")
                bc2.metric("Total Out", f"₹{money_out:,.2f}")
                bc3.metric(bal_label, f"₹{abs(net_bal):,.2f}", delta_color=delta_color)

                # 4. WHATSAPP GENERATOR (Includes Dates)

                wa_message = (
                    f"*Statement for: {selected_book}*\n"
                    f"📅 Period: {fmt_date(start_date)} to {fmt_date(end_date)}\n"
                    f"---------------------------\n"
                    f"✅ {msg_hindi}\n"
                    f"---------------------------\n"
                    f"Generated via JGMPS Ledger 2026."
                )
                encoded_msg = urllib.parse.quote(wa_message)
                whatsapp_url = f"https://wa.me/?text={encoded_msg}"

                st.markdown(f'''
                    <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                        <div style="background-color: #25D366; color: white; padding: 10px; text-align: center; border-radius: 8px; font-weight: bold; margin-top: 15px;">
                            📲 Send {start_date.strftime('%b')} Statement via WhatsApp
                        </div>
                    </a>
                ''', unsafe_allow_html=True)
                
                # --- FORMAL PDF / PRINT REPORT SECTION ---
                st.divider()
                if st.button(f"📄 Generate Formal Report ({fmt_date(start_date)} to {fmt_date(end_date)})", use_container_width=True, key="open_report"):
                    st.session_state['show_party_report'] = True

                if st.session_state.get('show_party_report', False):
                    with st.container(border=True):
                        # Header Section
                        st.markdown(f"""
                        <div style="text-align: center; font-family: sans-serif;">
                            <h2 style="margin-bottom: 0;">ACCOUNT STATEMENT</h2>
                            <h4 style="color: gray; margin-top: 5px;">{selected_book}</h4>
                            <p>Period: <b>{fmt_date(start_date)}</b> to <b>{fmt_date(end_date)}</b></p>
                            <hr>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Summary Row
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.write(f"**Total In:** ₹{money_in:,.2f}")
                        sc2.write(f"**Total Out:** ₹{money_out:,.2f}")
                        sc3.write(f"**Net Balance:** ₹{net_bal:,.2f}")
                        
                        st.write("---")
                        
                        # Transaction Table (using st.table for better print formatting)
                        report_display = filtered_df[['date', 'from_acc', 'to_acc', 'amount', 'note']].copy()
                        st.table(report_display)
                        
                        # ---- AFTER st.table(report_display) ----

                        pdf_file = generate_pdf(
                            selected_book,
                            start_date,
                            end_date,
                            report_display,
                            money_in,
                            money_out,
                            net_bal,
                            msg_hindi
                        )
                        
                        st.write("PDF size:", len(pdf_file))

                        st.download_button(
                            "🖨️ Download & Print PDF",
                            data=pdf_file,
                            file_name=f"{selected_book}_{fmt_date(start_date)}_statement.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                        st.markdown(f"""
                        <div style="margin-top: 20px; font-size: 12px; color: gray; text-align: center;">
                            <p>This is a computer-generated statement from JGMPS Ledger 2026.</p>
                            <p>Status: {msg_hindi}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("❌ Close Print View"):
                            st.session_state['show_party_report'] = False
                            st.rerun()
                    
            else:
                st.warning(f"No transactions found for {selected_book} between {fmt_date(start_date)} and {fmt_date(end_date)}.")
        
    with tab3:
        st.subheader("Search your Ledger")
        search = st.text_input("Type name or note to filter...", key="main_search_input")
        if search:
            filt = trans_df[trans_df.astype(str).apply(lambda x: search.lower() in x.str.lower().values, axis=1)]
            st.write(f"Found {len(filt)} matching records:")
            st.dataframe(filt, use_container_width=True)
            
            if not filt.empty:
                del_id = st.number_input("Enter ID to Delete", min_value=0, step=1, key="delete_id_input")
                if st.button("🗑️ Permanently Delete ID", key="delete_confirm_btn"):
                    run_action("DELETE FROM transactions WHERE id=?", (del_id,))
                    st.warning(f"Deleted transaction {del_id}")
                    st.rerun()

    with tab4:
 
        st.subheader("📑 Financial Reports & Export")
        
        # Determine the Hindi status for the business summary
        status_hindi = "मुनाफा (Profit)" if profit >= 0 else "नुकसान (Loss)"
        
        # Create a clean Hindi/English message
        report_text = (
            f"*MyLedger 2026 Summary*\n"
            f"---------------------------\n"
            f"📈 Total Sales: ₹{sales:,.2f}\n"
            f"📉 Expenses: ₹{expenses:,.2f}\n"
            f"💰 Net {status_hindi}: ₹{abs(profit):,.2f}\n"
            f"🎯 Margin: {margin_pct:.1f}%\n"
            f"---------------------------\n"
            f"Generated on: {datetime.now().strftime('%d %b, %Y')}"
        )
        
        encoded_text = urllib.parse.quote(report_text)
        whatsapp_url = f"https://wa.me/?text={encoded_text}"

        # FIXED: Changed 'unsafe_allow_phtml' to 'unsafe_allow_html'
        st.markdown(f'''
            <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">
                    📲 Share Business Summary to WhatsApp
                </div>
            </a>
        ''', unsafe_allow_html=True)
        
        # Row for basic exports
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            csv = trans_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Full Ledger (CSV)", 
                csv, 
                f"Ledger_Backup_{datetime.now().strftime('%Y-%m-%d')}.csv", 
                "text/csv", 
                use_container_width=True
            )
            
        with col_ex2:
            # Simple PDF Simulation / Print View
            if st.button("🖨️ Generate Print Report", use_container_width=True):
                st.info("Generating Report... Scroll down to see the Print View")
                st.session_state['show_report'] = True

        # --- THE PRINTABLE REPORT VIEW ---
        if st.session_state.get('show_report', False):
            st.divider()
            # This container mimics an A4 sheet look
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align: center;">
                    <h1>MyLedger Business Report</h1>
                    <p>Generated on: {datetime.now().strftime('%d %b %Y, %H:%M')}</p>
                    <hr>
                </div>
                """, unsafe_allow_html=True)
                
                # Report Metrics
                rc1, rc2, rc3 = st.columns(3)
                rc1.write(f"**Total Revenue:** ₹{sales:,.2f}")
                rc2.write(f"**Total Expenses:** ₹{expenses:,.2f}")
                rc3.write(f"**Net Profit:** ₹{profit:,.2f}")
                
                st.write("### Summary of Recent Transactions")
                # Show only the last 15 for a clean print
                st.table(trans_df.tail(15)[['date', 'from_acc', 'to_acc', 'amount']])
                
                st.markdown("---")
                st.caption("End of Report - MyLedger 2026 Management System")
                
                if st.button("Close Report"):
                    st.session_state['show_report'] = False
                    st.rerun()
                        
        st.divider()
                
        if st.button("🚨 Log Out", key="logout_btn"):
            st.session_state["authenticated"] = False
            st.rerun()