import streamlit as st
import student_app
import upload_tool
import auth

# --- Page Security Config ---
st.set_page_config(
    page_title="Study App Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Authentication ---
if not auth.check_password():
    st.stop()  # Do not continue if check_password is not True.

# --- Logged In Session ---
role = st.session_state.get("role")
username = st.session_state.get("username")

# --- Simple Routing ---
# Sidebar for navigation or info
with st.sidebar:
    st.write(f"Logged in as: **{username.capitalize()} ({role})**")
    if st.button("Logout"):
        auth.logout()
    st.markdown("---")

# Main Content Routing
if role == "student":
    student_app.app()
elif role == "teacher":
    upload_tool.app()
else:
    st.error("Invalid role detected. Please contact support.")
