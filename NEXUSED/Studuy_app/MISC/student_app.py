import streamlit as st
import json
import os
import asyncio
import logging

try:
    from integrated_app import app
except ImportError as e:
    st.error(f"Failed to import application logic: {e}")
    st.stop()

# --- Config & Setup ---
# Removed st.set_page_config as it will be called in the main app

# --- Helpers ---
def load_topics():
    """Load available study topics from the registry."""
    if os.path.exists("topics.json"):
        try:
            with open("topics.json", "r") as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"Error loading topics: {e}")
    return []

# --- Main Interface ---
def app():
    # Sidebar
    with st.sidebar:
        st.header("🎓 Study Controls")
        st.markdown("Select a module to focus your study session.")
        
        topics = load_topics()
        if not topics:
            st.warning("⚠️ No topics found.\n\nAsk your teacher to upload content using the Upload Tool.")
            selected_topic = None
        else:
            selected_topic = st.radio("📚 Available Topics", topics)
            st.info(f"Focusing on: **{selected_topic}**")

        st.markdown("---")
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Main Area
    st.title("Student Study assistant")
    st.markdown("Ask questions based on your selected study module.")

    if not selected_topic:
        st.info("👈 Please wait for topics to be available or select one from the sidebar.")
        return

    # Chat State
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": f"Hello! I'm ready to help you specific to **{selected_topic}**. What's on your mind?"}]

    # Render Chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input
    if prompt := st.chat_input("Type your question here..."):
        # User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            try:
                # Async execution wrapper
                async def run_query():
                    inputs = {"question": prompt, "namespace": selected_topic}
                    return await app.ainvoke(inputs)
                
                result = asyncio.run(run_query())
                answer = result.get("final_answer", "I could not generate an answer.")
                
                message_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                message_placeholder.error(f"An error occurred: {e}")

if __name__ == "__main__":
    app()
