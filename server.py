"""
Multi-PDF RAG — Flask Backend
--------------------------------
Serves a REST API on top of rag_system.py's core logic (PDF processing,
chunking, ChromaDB, Ollama), and serves the static HTML/CSS/JS frontend.

Setup (one time):
    pip install flask chromadb sentence-transformers pypdf ollama --break-system-packages
    ollama pull llama3

Run:
    python server.py

Then open http://localhost:5000 in your browser.
"""

import os
import tempfile

from flask import Flask, jsonify, request, send_from_directory

from rag_system import (
    add_pdfs,
    answer_question,
    get_collection,
    get_unique_sources,
    load_history_records,
    search_history,
)

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.route("/api/status")
def api_status():
    """Returns dashboard stats: pdf count, chunk count, question count."""
    try:
        chunk_count = get_collection().count()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    sources = get_unique_sources()
    history = load_history_records()

    return jsonify({
        "pdf_count": len(sources),
        "chunk_count": chunk_count,
        "question_count": len(history),
        "sources": sources,
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Accepts one or more PDF files (multipart/form-data, field name 'files'),
    saves them to a temp dir, and ingests them into the knowledge base."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    tmp_dir = tempfile.mkdtemp()
    saved_paths = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            continue
        path = os.path.join(tmp_dir, f.filename)
        f.save(path)
        saved_paths.append(path)

    if not saved_paths:
        return jsonify({"error": "No valid PDF files found"}), 400

    try:
        add_pdfs(saved_paths)
    except Exception as e:
        return jsonify({"error": f"Failed to process PDFs: {e}"}), 500

    return jsonify({
        "success": True,
        "processed": [os.path.basename(p) for p in saved_paths],
        "chunk_count": get_collection().count(),
    })


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Body: {"question": "..."}. Returns answer + source chunks used."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    if get_collection().count() == 0:
        return jsonify({
            "answer": "No documents in the knowledge base yet — upload a PDF first.",
            "chunks": [],
        })

    answer, chunks = answer_question(question, return_chunks=True)
    return jsonify({"answer": answer, "chunks": chunks})


@app.route("/api/history")
def api_history():
    records = load_history_records()
    return jsonify({"history": list(reversed(records))})


@app.route("/api/history/search")
def api_history_search():
    """?q=keyword — searches past Q&A by keyword(s), returns newest first."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Query param 'q' is required"}), 400
    results = search_history(query)
    return jsonify({"query": query, "count": len(results), "results": results})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)