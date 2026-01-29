import streamlit as st
from db_helpers import (
    get_all_groups,
    add_account,
    get_all_accounts,
    update_account,
    toggle_account_status
)

st.set_page_config(page_title="Accounts Master", layout="wide")

st.title("👤 Accounts Master")

# -------------------------------
# Add New Account
# -------------------------------
st.subheader("➕ Add New Account")

groups = get_all_groups()

if not groups:
    st.warning("⚠️ Please create Groups first before adding Accounts.")
    st.stop()

group_labels = [g["group_name"] for g in groups]
group_map = {g["group_name"]: g["id"] for g in groups}
group_reverse_map = {g["id"]: g["group_name"] for g in groups}

with st.form("add_account_form"):
    col1, col2 = st.columns(2)

    with col1:
        acc_name = st.text_input("Account Name *")
        phone = st.text_input("Phone (optional)")

    with col2:
        selected_group = st.selectbox("Select Group *", group_labels)
        address = st.text_input("Address (optional)")

    submitted = st.form_submit_button("Save Account")

    if submitted:
        if not acc_name.strip():
            st.warning("⚠️ Account name is required")
        else:
            try:
                group_id = group_map[selected_group]
                add_account(acc_name, group_id, phone, address)
                st.success(f"✅ Account '{acc_name}' added successfully")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.divider()

# -------------------------------
# Existing Accounts
# -------------------------------
st.subheader("📋 Existing Accounts")

accounts = get_all_accounts()

if not accounts:
    st.info("No accounts found.")
else:
    for a in accounts:
        with st.expander(f"👤 {a['name']} ({a['group_name']})", expanded=False):
            col1, col2, col3 = st.columns([3, 3, 2])

            with col1:
                new_name = st.text_input(
                    "Account Name",
                    value=a["name"],
                    key=f"name_{a['id']}"
                )
                new_phone = st.text_input(
                    "Phone",
                    value=a["phone"] or "",
                    key=f"phone_{a['id']}"
                )

            with col2:
                new_group = st.selectbox(
                    "Group",
                    group_labels,
                    index=group_labels.index(group_reverse_map[a["group_id"]]),
                    key=f"group_{a['id']}"
                )
                new_address = st.text_input(
                    "Address",
                    value=a.get("address", "") or "",
                    key=f"address_{a['id']}"
                )

            with col3:
                st.markdown("### Actions")

                if st.button("💾 Update", key=f"update_{a['id']}"):
                    try:
                        update_account(
                            a["id"],
                            new_name,
                            group_map[new_group],
                            new_phone,
                            new_address
                        )
                        st.success("✅ Account updated")
                        st.rerun()
                    except Exception as e:
                        st.error(e)

                status_label = "Deactivate ❌" if a["is_active"] == 1 else "Activate ✅"

                if st.button(status_label, key=f"toggle_{a['id']}"):
                    try:
                        toggle_account_status(
                            a["id"],
                            0 if a["is_active"] == 1 else 1
                        )
                        st.success("✅ Status changed")
                        st.rerun()
                    except Exception as e:
                        st.error(e)
