"""
Multi-PDF RAG — Web UI (Streamlit)
------------------------------------
A colorful, browser-based front end for rag_system.py. Reuses all the core
logic (PDF processing, chunking, ChromaDB, Ollama) from rag_system.py —
this file is purely the UI layer.

Setup (one time):
    pip install streamlit chromadb sentence-transformers pypdf ollama --break-system-packages
    ollama pull llama3

Run:
    streamlit run app.py
"""

import contextlib
import io
import json
import os
import tempfile

import streamlit as st

from rag_system import (
    add_pdfs,
    answer_question,
    get_collection,
    get_unique_sources,
    HISTORY_FILE,
)

st.set_page_config(page_title="PDFpulse", page_icon="🩵", layout="wide")

# ---------------------------------------------------------------------------
# Custom CSS — colorful / playful theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(160deg, #fdf2ff 0%, #f0f7ff 50%, #fff9f0 100%);
    }

    /* Header banner */
    .pdfpulse-header {
        background: linear-gradient(120deg, #7c3aed, #ec4899, #f59e0b);
        padding: 28px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(124, 58, 237, 0.25);
    }
    .pdfpulse-header h1 {
        color: white;
        margin: 0;
        font-size: 2.1rem;
    }
    .pdfpulse-header p {
        color: rgba(255,255,255,0.9);
        margin: 4px 0 0 0;
        font-size: 1rem;
    }

    /* Stat cards */
    .stat-card {
        border-radius: 16px;
        padding: 18px 20px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    }
    .stat-card .num { font-size: 2rem; font-weight: 800; line-height: 1.1; }
    .stat-card .label { font-size: 0.85rem; opacity: 0.9; margin-top: 4px; }
    .stat-1 { background: linear-gradient(135deg, #7c3aed, #a78bfa); }
    .stat-2 { background: linear-gradient(135deg, #ec4899, #f472b6); }
    .stat-3 { background: linear-gradient(135deg, #f59e0b, #fbbf24); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ede9fe, #fce7f3);
    }

    /* Doc pill */
    .doc-pill {
        display: inline-block;
        background: white;
        border: 1.5px solid #d8b4fe;
        color: #6d28d9;
        padding: 4px 12px;
        border-radius: 999px;
        margin: 3px 4px 3px 0;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Source chunk card */
    .source-chunk {
        background: #faf5ff;
        border-left: 4px solid #a855f7;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 0.88rem;
    }
    .source-chunk .meta {
        color: #a855f7;
        font-weight: 700;
        font-size: 0.78rem;
        margin-bottom: 4px;
    }

    /* Example question chips */
    .stButton button {
        border-radius: 999px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []  # list of {"role", "content", "chunks"(optional)}
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


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


def render_source_chunk(c):
    text = c["text"][:400] + ("..." if len(c["text"]) > 400 else "")
    st.markdown(
        f'<div class="source-chunk">'
        f'<div class="meta">📄 {c["source"]} · page {c["page"]}</div>'
        f'{text}'
        f'</div>',
        unsafe_allow_html=True,
    )


EXAMPLE_QUESTIONS = [
    "📝 Summarize this document",
    "🔑 What are the key points?",
    "❓ What questions does this answer?",
]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="pdfpulse-header">
    <h1>🩵 PDFpulse</h1>
    <p>Upload PDFs, ask anything, get grounded answers with citations — powered by your own local AI.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — PDF upload + knowledge base status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📤 Add documents")
    uploaded_files = st.file_uploader(
        "Upload PDF(s)", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed"
    )

    if uploaded_files and st.button("✨ Process PDFs", use_container_width=True, type="primary"):
        tmp_dir = tempfile.mkdtemp()
        saved_paths = []
        for uf in uploaded_files:
            path = os.path.join(tmp_dir, uf.name)
            with open(path, "wb") as f:
                f.write(uf.getbuffer())
            saved_paths.append(path)

        with st.spinner(f"🔮 Reading {len(saved_paths)} file(s)... (first run also downloads the embedding model)"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                add_pdfs(saved_paths)

        st.success("Done! Your documents are ready to chat with. 🎉")
        st.rerun()

    st.divider()

    st.markdown("### 📚 Your library")
    sources = get_unique_sources()
    if sources:
        pills = "".join(f'<span class="doc-pill">📄 {s}</span>' for s in sources)
        st.markdown(pills, unsafe_allow_html=True)
    else:
        st.info("No PDFs yet — upload one above to get started.")

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat = []
        st.rerun()


# ---------------------------------------------------------------------------
# Stats dashboard
# ---------------------------------------------------------------------------
chunk_count = get_doc_count()
pdf_count = len(get_unique_sources())
question_count = len(load_history_records())

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="stat-card stat-1"><div class="num">{pdf_count}</div><div class="label">📄 PDFs loaded</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card stat-2"><div class="num">{chunk_count}</div><div class="label">🧩 Chunks indexed</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card stat-3"><div class="num">{question_count}</div><div class="label">💬 Questions asked</div></div>', unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------------------------
# Main area — tabs for Chat and History
# ---------------------------------------------------------------------------
tab_chat, tab_history = st.tabs(["💬  Chat", "🕒  History"])

with tab_chat:
    if not st.session_state.chat:
        st.markdown("##### 💡 Try asking:")
        cols = st.columns(len(EXAMPLE_QUESTIONS))
        for col, ex in zip(cols, EXAMPLE_QUESTIONS):
            with col:
                if st.button(ex, use_container_width=True):
                    st.session_state.pending_question = ex.split(" ", 1)[1]

    for msg in st.session_state.chat:
        avatar = "🙋" if msg["role"] == "user" else "🩵"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("chunks"):
                with st.expander(f"📎 View {len(msg['chunks'])} source(s) used"):
                    for c in msg["chunks"]:
                        render_source_chunk(c)

    typed_question = st.chat_input("Ask a question about your PDFs...")
    question = st.session_state.pending_question or typed_question
    st.session_state.pending_question = None

    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🙋"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="🩵"):
            if get_doc_count() == 0:
                answer = "No documents in the knowledge base yet — upload a PDF from the sidebar first. 📤"
                chunks = []
                st.warning(answer)
            else:
                with st.spinner("🧠 Thinking..."):
                    answer, chunks = answer_question(question, return_chunks=True)
                st.markdown(answer)
                if chunks:
                    with st.expander(f"📎 View {len(chunks)} source(s) used"):
                        for c in chunks:
                            render_source_chunk(c)

        st.session_state.chat.append({"role": "assistant", "content": answer, "chunks": chunks})

with tab_history:
    st.markdown("##### 🕒 Everything you've asked so far")
    records = load_history_records()

    if not records:
        st.info("No history yet — ask a question in the Chat tab first.")
    else:
        for rec in reversed(records):
            with st.expander(f"🗨️ {rec['question']}  ·  {rec['timestamp']}"):
                st.markdown(f"**Q:** {rec['question']}")
                st.markdown(f"**A:** {rec['answer']}")
                if rec.get("sources"):
                    pills = "".join(f'<span class="doc-pill">📄 {s}</span>' for s in rec["sources"])
                    st.markdown(pills, unsafe_allow_html=True)