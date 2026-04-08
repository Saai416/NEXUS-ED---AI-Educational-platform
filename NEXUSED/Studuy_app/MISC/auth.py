import streamlit as st

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["login_username"] == "student" and st.session_state["login_password"] == "student123":
            st.session_state["password_correct"] = True
            st.session_state["role"] = "student"
            st.session_state["username"] = st.session_state["login_username"] # Persist username
            del st.session_state["login_password"]  # don't store password
        elif st.session_state["login_username"] == "teacher" and st.session_state["login_password"] == "teacher123":
            st.session_state["password_correct"] = True
            st.session_state["role"] = "teacher"
            st.session_state["username"] = st.session_state["login_username"] # Persist username
            del st.session_state["login_password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", key="login_username")
        st.text_input("Password", type="password", on_change=password_entered, key="login_password")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", key="login_username")
        st.text_input("Password", type="password", on_change=password_entered, key="login_password")
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

def logout():
    """Logs the user out."""
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    if "role" in st.session_state:
        del st.session_state["role"]
    if "username" in st.session_state:
        del st.session_state["username"]
    st.rerun()
