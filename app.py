"""
Multi-PDF RAG — Web UI (Streamlit)
------------------------------------
A simple browser-based front end for rag_system.py. Reuses all the same
core logic (PDF processing, chunking, ChromaDB, Ollama) — this file just
wraps it in a UI.

Setup (one time):
    pip install streamlit chromadb sentence-transformers pypdf ollama --break-system-packages
    ollama pull llama3

Run:
    streamlit run app.py

This opens a browser tab automatically (usually http://localhost:8501).
"""

import os
import tempfile

import streamlit as st

from rag_system import (
    add_pdfs,
    answer_question,
    get_collection,
    HISTORY_FILE,
)
import json

st.set_page_config(page_title="PDFpulse — Multi-PDF RAG", page_icon="📄", layout="wide")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []  # list of {"role": "user"/"assistant", "content": str}


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
# Sidebar — PDF upload + knowledge base status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📄 PDFpulse")
    st.caption("Multi-PDF RAG system")

    st.subheader("Add documents")
    uploaded_files = st.file_uploader(
        "Upload PDF(s)", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files and st.button("Process PDFs", use_container_width=True):
        tmp_dir = tempfile.mkdtemp()
        saved_paths = []
        for uf in uploaded_files:
            path = os.path.join(tmp_dir, uf.name)
            with open(path, "wb") as f:
                f.write(uf.getbuffer())
            saved_paths.append(path)

        with st.spinner(f"Processing {len(saved_paths)} file(s)... (first run also downloads the embedding model)"):
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                add_pdfs(saved_paths)

        st.success(buf.getvalue().strip().splitlines()[-1] if buf.getvalue().strip() else "Done.")
        st.rerun()

    st.divider()
    count = get_doc_count()
    st.metric("Chunks in knowledge base", count)
    if count == 0:
        st.info("Upload a PDF above to get started.")

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat = []
        st.rerun()


# ---------------------------------------------------------------------------
# Main area — tabs for Chat and History
# ---------------------------------------------------------------------------
tab_chat, tab_history = st.tabs(["💬 Chat", "🕒 History"])

with tab_chat:
    st.header("Ask your documents")

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask a question about your PDFs...")

    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            if get_doc_count() == 0:
                answer = "No documents in the knowledge base yet — upload a PDF from the sidebar first."
                st.warning(answer)
            else:
                with st.spinner("Thinking..."):
                    answer = answer_question(question)
                st.markdown(answer)

        st.session_state.chat.append({"role": "assistant", "content": answer})

with tab_history:
    st.header("Past Q&A")
    records = load_history_records()

    if not records:
        st.info("No history yet — ask a question in the Chat tab first.")
    else:
        for rec in reversed(records):
            with st.expander(f"{rec['timestamp']} — {rec['question']}"):
                st.markdown(f"**Q:** {rec['question']}")
                st.markdown(f"**A:** {rec['answer']}")
                if rec.get("sources"):
                    st.caption(f"Sources: {', '.join(rec['sources'])}")