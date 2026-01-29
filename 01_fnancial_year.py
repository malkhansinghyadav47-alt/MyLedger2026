import streamlit as st
from datetime import date

from db_helpers import (
    get_active_financial_year,
    get_all_financial_years,
    set_active_financial_year,
    add_financial_year,
    update_financial_year,
    delete_financial_year,
    can_delete_financial_year,
    indian_date
)

st.set_page_config(page_title="Financial Year Setup", layout="wide")
st.title("📅 Financial Year Management")

# ===============================
# CURRENT ACTIVE YEAR
# ===============================
active_year = get_active_financial_year()

st.subheader("🔁 Current Active Financial Year")
if active_year:
    st.success(
        f"Active Year: {active_year['label']} "
        f"({indian_date(active_year['start_date'])} to {indian_date(active_year['end_date'])})"
    )
else:
    st.warning("⚠️ No active financial year selected")

st.divider()

# ===============================
# ADD FINANCIAL YEAR
# ===============================
st.subheader("➕ Add Financial Year")

with st.form("add_fy"):
    label = st.text_input(
        "Financial Year",
        placeholder="e.g. 2049-50"
    )

    submitted = st.form_submit_button("Add Financial Year")

    if submitted:
        success, msg = add_financial_year(label)

        if success:
            st.success("✅ Financial Year added successfully")
            st.rerun()
        else:
            st.warning(f"⚠️ {msg}")


st.divider()

# ===============================
# ALL FINANCIAL YEARS
# ===============================
st.subheader("📋 All Financial Years")

years = get_all_financial_years()
if not years:
    st.info("No financial years found")
    st.stop()

for y in years:
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 3, 3, 2])

        col1.write(f"**{y['label']}**")
        col2.write(indian_date(y["start_date"]))
        col3.write(indian_date(y["end_date"]))

        if y["is_active"] == 1:
            col4.success("ACTIVE")
        else:
            if col4.button("Set Active", key=f"active_{y['id']}"):
                set_active_financial_year(y["id"])
                st.rerun()

        with st.expander("✏️ Edit / ❌ Delete"):
            new_label = st.text_input(
                "Financial Year (YYYY-YY)",
                y["label"],
                key=f"lbl_{y['id']}"
            )

            if st.button("Update", key=f"upd_{y['id']}"):
                try:
                    update_financial_year(y["id"], new_label)
                    st.success("✅ Financial Year updated")
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))

            if can_delete_financial_year(y["id"]):
                if st.button("❌ Delete", key=f"del_{y['id']}"):
                    delete_financial_year(y["id"])
                    st.warning("Deleted")
                    st.rerun()
            else:
                st.info("Cannot delete (used in accounts / transactions)")
