import streamlit as st
from db_helpers import add_group, get_all_groups
from db_helpers import update_group, delete_group, can_delete_group

st.set_page_config(page_title="Account Groups", layout="wide")

st.title("🏷 Account Groups Management")

# -------------------------------
# Add New Group
# -------------------------------
st.subheader("➕ Add New Group")

with st.form("add_group_form"):
    group_name = st.text_input("Group Name", placeholder="e.g. Assets, Income, Expenses")
    submitted = st.form_submit_button("Save Group")

    if submitted:
        if not group_name.strip():
            st.warning("⚠️ Group name cannot be empty")
        else:
            try:
                add_group(group_name)
                st.success(f"✅ Group '{group_name}' added successfully")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.divider()

# -------------------------------
# Show All Groups
# -------------------------------

st.subheader("📋 Existing Groups")

groups = get_all_groups()

if not groups:
    st.info("No groups found.")
    st.stop()

for g in groups:
    with st.container(border=True):
        col1, col2 = st.columns([3, 2])

        col1.write(f"**{g['group_name']}**")

        with col2:
            with st.expander("✏️ Edit / ❌ Delete"):
                new_name = st.text_input(
                    "Group Name",
                    g["group_name"],
                    key=f"grp_{g['id']}"
                )

                if st.button("Update", key=f"upd_{g['id']}"):
                    try:
                        update_group(g["id"], new_name)
                        st.success("✅ Group updated")
                        st.rerun()
                    except ValueError as e:
                        st.warning(str(e))

                if can_delete_group(g["id"]):
                    if st.button("❌ Delete", key=f"del_{g['id']}"):
                        delete_group(g["id"])
                        st.warning("🗑 Group deleted")
                        st.rerun()
                else:
                    st.info("🔒 Cannot delete (accounts exist)")
