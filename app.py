# app.py
import streamlit as st
from agents import CoordinatorAgent

st.set_page_config(page_title="AI Algorithm Agent", page_icon="🤖", layout="wide")

# Modern Styling Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .stButton>button {
        background: linear-gradient(135deg, #3B82F6, #8B5CF6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    h1 {
        background: linear-gradient(to right, #60A5FA, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 AI-Powered Algorithm Generation & Explanation Agent")
st.write("A task-oriented multi-agent assistant to generate, explain, and analyze code structures.")

# Sidebar Configuration
st.sidebar.header("⚙️ Agent Settings")
api_provider = st.sidebar.selectbox("LLM Provider", ["gemini", "openai"])
target_lang = st.sidebar.selectbox("Programming Language", ["Python", "C++", "Java", "JavaScript"])

# Sidebar Info
st.sidebar.divider()
st.sidebar.caption("**Note:** Free-tier Gemini API has ~20 requests/day limit. "
                    "If you get rate-limit errors, wait 1 minute and try again.")

# Main Input Form
with st.form("agent_form"):
    algo_name = st.text_input("Algorithm Name", placeholder="e.g., Dijkstra's Shortest Path, Merge Sort, A*")
    user_query = st.text_area("Your Question / Prompt", 
                              placeholder="e.g., Write the algorithm in Python, explain how it works step-by-step, and calculate its average time complexity.")
    submit_btn = st.form_submit_button("🚀 Run Agent Pipeline")

if submit_btn:
    if not algo_name or not user_query:
        st.warning("Please fill in both the Algorithm Name and Your Query!")
    else:
        coordinator = CoordinatorAgent()
        
        with st.spinner("🔄 Querying Gemini API... This may take up to 60 seconds if rate-limited."):
            response_md = coordinator.process_query(
                query=user_query, 
                algorithm=algo_name, 
                language=target_lang, 
                provider=api_provider
            )
            
        st.success("✅ Pipeline executed successfully!")
        st.markdown(response_md)
        
        with st.expander("📋 Copy Raw Output"):
            st.code(response_md, language="markdown")
