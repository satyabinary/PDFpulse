import os
import tempfile
import json
import streamlit as st

# Import core RAG functions
from rag_system import (
    add_pdfs,
    answer_question,
    get_collection,
    HISTORY_FILE,
)

# ---------------------------------------------------------------------------
# PAGE CONFIGURATION (PREMIUM LOOK)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PDFpulse — Advanced Multi-PDF RAG",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# CUSTOM CSS FOR ULTRA-MODERN GLOW & CLASSY THEME
# ---------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Typography Reset */
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Custom Theme Gradient Background */
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 10% 20%, rgba(18, 16, 32, 1) 0%, rgba(10, 10, 15, 1) 100%);
    }
    
    /* Glassmorphic Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(18, 18, 30, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Neon Glow & Pulse animations */
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.4); }
        70% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(124, 58, 237, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(124, 58, 237, 0); }
    }
    
    .pulse-glow {
        animation: pulse 2s infinite;
        border: 2px solid #7c3aed !important;
    }

    /* Gradient Text & Titles */
    .hero-title {
        background: linear-gradient(135deg, #a78bfa 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 5px;
    }

    /* Custom Cards */
    .dashboard-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        transition: all 0.3s ease;
        margin-bottom: 15px;
    }
    .dashboard-card:hover {
        border-color: rgba(124, 58, 237, 0.5);
        transform: translateY(-2px);
    }

    /* Live Badge Indicator */
    .badge-ready {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 10px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .badge-empty {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 4px 10px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Beautiful Chat Avatars & Containers */
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 15px !important;
        padding: 15px !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: rgba(124, 58, 237, 0.08) !important;
        border: 1px solid rgba(124, 58, 237, 0.15) !important;
    }
    
    /* Interactive Quick Start Cards */
    .quick-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 15px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
    }
    .quick-card:hover {
        background: rgba(124, 58, 237, 0.08);
        border-color: rgba(124, 58, 237, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []
if "clicked_prompt" not in st.session_state:
    st.session_state.clicked_prompt = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_doc_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0

def load_history_records():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

# ---------------------------------------------------------------------------
# Sidebar — Redesigned with Glassmorphism & Status indicators
# ---------------------------------------------------------------------------
with st.sidebar:
    # Logo with custom glow
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px; padding-top:10px;">
            <div style="background: linear-gradient(135deg, #7c3aed, #3b82f6); width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);">
                <span style="font-size: 20px; color: white;">⚡</span>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">PDF<span style="color: #a78bfa;">pulse</span></h2>
                <span style="font-size: 0.75rem; color: #9ca3af; letter-spacing: 1px; text-transform: uppercase;">Next-Gen RAG System</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Dynamic status pill
    doc_count = get_doc_count()
    if doc_count > 0:
        st.markdown('<div class="badge-ready"><span style="color: #10b981;">●</span> Engine Online — Ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-empty"><span style="color: #f59e0b;">●</span> Waiting for Uploads</div>', unsafe_allow_html=True)

    st.write("") # Spacer

    # Drop zone section
    st.markdown("<h4 style='margin-bottom:0px; font-weight: 600;'>📁 Upload Documents</h4>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload PDF files to start context indexing", 
        type=["pdf"], 
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        st.markdown(f"<p style='font-size:0.85rem; color:#a78bfa;'>📎 Loaded {len(uploaded_files)} PDF(s)</p>", unsafe_allow_html=True)
        if st.button("🚀 Index Documents", use_container_width=True, type="primary"):
            tmp_dir = tempfile.mkdtemp()
            saved_paths = []
            for uf in uploaded_files:
                path = os.path.join(tmp_dir, uf.name)
                with open(path, "wb") as f:
                    f.write(uf.getbuffer())
                saved_paths.append(path)

            with st.spinner("⚡ Parsing & Indexing into ChromaDB... Please wait."):
                import io
                import contextlib
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    add_pdfs(saved_paths)

            st.balloons()
            st.success("Successfully vectorized database!")
            st.rerun()

    st.markdown("---")
    
    # System Metrics Display Card
    st.markdown("""
        <div class="dashboard-card">
            <span style="color: #9ca3af; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Vector Engine Data</span>
            <h3 style="margin: 5px 0; font-size: 2rem; font-weight: 700; color: #f3f4f6;">{}</h3>
            <span style="color: #a78bfa; font-size: 0.8rem;">Chunks available in KB</span>
        </div>
    """.format(doc_count), unsafe_allow_html=True)

    # Clear Chat with warning styling
    if st.button("🗑️ Clear Active Sessions", use_container_width=True):
        st.session_state.chat = []
        st.session_state.clicked_prompt = None
        st.rerun()

# ---------------------------------------------------------------------------
# Main workspace layout (Cleaned and Modernized)
# ---------------------------------------------------------------------------
st.markdown("<p style='margin-bottom:0.2rem; color: #a78bfa; font-weight: 600; text-transform: uppercase; font-size:0.8rem; letter-spacing: 1.5px;'>AI CO-PILOT ASSISTANT</p>", unsafe_allow_html=True)
st.markdown("<h1 class='hero-title'>Empower Your Documents</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af; font-size: 1.1rem; margin-top: -10px;'>Chat inside a localized context space powered by Llama-3 & Embeddings.</p>", unsafe_allow_html=True)

# Main tabs switcher
tab_chat, tab_history = st.tabs(["💬 Dynamic Chat", "🕒 History Log"])

with tab_chat:
    # Onboarding State (If chat is empty)
    if not st.session_state.chat:
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%); border: 1px solid rgba(124, 58, 237, 0.15); border-radius: 20px; padding: 40px; text-align: center; margin: 30px 0;">
                <span style="font-size: 3.5rem;">🧠</span>
                <h3 style="margin-top: 15px; font-weight: 700; font-size:1.6rem;">No conversations active</h3>
                <p style="color: #9ca3af; max-width: 500px; margin: 0 auto 20px auto;">Upload documents to build your private local knowledge base. Once done, ask anything inside the prompt container below!</p>
            </div>
        """, unsafe_allow_html=True)

        # Suggested/Quick Start Questions
        if doc_count > 0:
            st.markdown("##### ⚡ Quick Start Prompts")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📋 Summarize key findings from documents.", use_container_width=True):
                    st.session_state.clicked_prompt = "Summarize the key findings and highlights from the uploaded documents."
            with col2:
                if st.button("🛡️ What are the potential risks identified?", use_container_width=True):
                    st.session_state.clicked_prompt = "Explain any risks, warnings or concerns mentioned in the source texts."
            with col3:
                if st.button("📊 List action items and methodology.", use_container_width=True):
                    st.session_state.clicked_prompt = "Extract and list the bulleted actionable points or methodologies mentioned."

    # Render Active Chats
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle clickable quick start buttons
    if st.session_state.clicked_prompt:
        question = st.session_state.clicked_prompt
        st.session_state.clicked_prompt = None # Reset
    else:
        question = st.chat_input("Ask a question about your uploaded PDFs...")

    # Execute RAG query logic
    if question:
        # Append User Msg
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Append Assistant response
        with st.chat_message("assistant"):
            if doc_count == 0:
                answer = "Error: System context is empty! Please drop one or more PDF files on the sidebar drag-and-drop zone first."
                st.error(answer)
            else:
                with st.status("🧠 Analyzing system context & generating answer...", expanded=False) as status:
                    st.write("Searching database vectors...")
                    # Simulating step response for smoother UX
                    answer = answer_question(question)
                    status.update(label="Complete analysis verified!", state="complete", expanded=False)
                
                # Render beautifully formatted Markdown
                st.markdown(answer)

        st.session_state.chat.append({"role": "assistant", "content": answer})
        st.rerun()

# ---------------------------------------------------------------------------
# History tab — Premium Timelines Card look
# ---------------------------------------------------------------------------
with tab_history:
    st.markdown("<h3 style='font-weight: 700; margin-bottom: 10px;'>📊 Past Activity Logs</h3>", unsafe_allow_html=True)
    records = load_history_records()

    if not records:
        st.info("No past logs recorded on disk. Ask your first query to log conversations dynamically.")
    else:
        for idx, rec in enumerate(reversed(records)):
            with st.container():
                st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.02); border-left: 3px solid #7c3aed; padding: 15px; margin-bottom:15px; border-radius: 0 12px 12px 0;">
                        <span style="font-size:0.75rem; color:#9ca3af;">⏱️ Logs at: {rec['timestamp']}</span>
                        <h4 style="margin: 5px 0 10px 0; font-weight: 600;">Q: {rec['question']}</h4>
                        <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; font-size: 0.92rem; color: #d1d5db; line-height: 1.6;">
                            <strong>A:</strong> {rec['answer']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if rec.get("sources"):
                    st.markdown(f"<p style='font-size: 0.8rem; margin-top:-10px; padding-left:15px; color:#a78bfa;'>🎯 Source files: <code>{', '.join(rec['sources'])}</code></p>", unsafe_allow_html=True)