"""
Multi-PDF RAG System
---------------------
Ingests multiple PDFs, chunks + embeds them into ChromaDB, and answers
user questions by retrieving relevant chunks and summarizing them with
a local LLM (via Ollama).

Setup (one time):
    pip install chromadb sentence-transformers pypdf ollama --break-system-packages
    ollama pull llama3        # or any model you like (mistral, phi3, etc.)
    ollama serve               # run the local LLM server (usually auto-starts)

Usage:
    python rag_system.py --add /path/to/pdf1.pdf /path/to/pdf2.pdf
    python rag_system.py --ask
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_DIR = "./chroma_db"
COLLECTION_NAME = "pdf_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"   # small, fast, good enough for most PDFs
CHUNK_SIZE = 800                    # target characters per chunk
CHUNK_OVERLAP = 150                 # overlap between chunks (in sentences' worth of chars)
TOP_K = 5                           # chunks retrieved per question
OLLAMA_MODEL = "llama3"             # change to whatever model you've pulled
HISTORY_FILE = "./history.jsonl"    # Q&A log, one JSON object per line

# Sentence boundary: split after ., !, or ? followed by whitespace + capital/quote,
# but not on common abbreviations (Mr., Dr., e.g., etc.) — good-enough heuristic
# without pulling in an NLP library.
_ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc", "e.g", "i.e", "fig", "no"}
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


# ---------------------------------------------------------------------------
# PDF loading + chunking
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Returns list of (page_number, page_text)."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append((i + 1, text))
    return pages


def split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences, collapsing whitespace. Avoids cutting on
    common abbreviations (Mr., Dr., etc.) using a simple heuristic."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    raw_sentences = _SENTENCE_SPLIT_RE.split(text)

    # Merge back any split that happened right after a known abbreviation
    sentences = []
    for s in raw_sentences:
        if sentences:
            prev = sentences[-1]
            last_word = prev.rstrip(".!?").split()[-1].lower() if prev.split() else ""
            if last_word in _ABBREVIATIONS:
                sentences[-1] = prev + " " + s
                continue
        sentences.append(s)

    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Sentence-aware chunker: packs whole sentences into ~chunk_size chunks
    instead of cutting mid-word/mid-sentence. Keeps the last few sentences of
    a chunk as overlap context for the next one, so retrieval doesn't lose
    meaning at chunk boundaries."""
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sent_len = len(sentence) + 1  # +1 for the joining space

        # A single sentence longer than chunk_size: emit it as its own chunk.
        if sent_len > chunk_size and not current:
            chunks.append(sentence)
            continue

        if current_len + sent_len > chunk_size and current:
            chunks.append(" ".join(current))

            # Build overlap: keep trailing sentences that fit within `overlap` chars
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) + 1 > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_len += len(s) + 1
            current = overlap_sentences
            current_len = overlap_len

        current.append(sentence)
        current_len += sent_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def process_pdf(pdf_path: str) -> list[dict]:
    """Returns list of dicts: {id, text, metadata}."""
    pdf_name = Path(pdf_path).name
    pages = extract_text_from_pdf(pdf_path)

    records = []
    for page_num, page_text in pages:
        for chunk in chunk_text(page_text):
            records.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "metadata": {"source": pdf_name, "page": page_num},
            })
    return records


# ---------------------------------------------------------------------------
# Vector store (ChromaDB)
# ---------------------------------------------------------------------------
def get_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )
    return collection


def add_pdfs(pdf_paths: list[str]):
    collection = get_collection()

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"[skip] File not found: {pdf_path}")
            continue

        print(f"[+] Processing {pdf_path} ...")
        records = process_pdf(pdf_path)

        if not records:
            print(f"    No extractable text found (maybe scanned images?). Skipping.")
            continue

        collection.add(
            ids=[r["id"] for r in records],
            documents=[r["text"] for r in records],
            metadatas=[r["metadata"] for r in records],
        )
        print(f"    Added {len(records)} chunks from {Path(pdf_path).name}")

    print(f"\nDone. Total chunks in DB: {collection.count()}")


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[question], n_results=top_k)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": doc, "source": meta["source"], "page": meta["page"], "score": dist})
    return hits


# ---------------------------------------------------------------------------
# Answer generation (local LLM via Ollama)
# ---------------------------------------------------------------------------
def build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = []
    for c in chunks:
        context_blocks.append(f"[Source: {c['source']}, Page {c['page']}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""You are a helpful assistant answering questions using ONLY the provided context from PDF documents.
If the answer isn't in the context, say so clearly instead of guessing.
Always cite the source filename and page number for each fact you use.

Context:
{context}

Question: {question}

Give a clear, well-organized answer with citations like (source.pdf, p.X)."""
    return prompt


def ask_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    try:
        import ollama
    except ImportError:
        return ("[Ollama python package not installed. Run:\n"
                "  pip install ollama --break-system-packages\n"
                "and make sure `ollama serve` is running with a pulled model.]")

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
    except Exception as e:
        return (f"[Error calling Ollama: {e}\n"
                f"Make sure Ollama is running (`ollama serve`) and model '{model}' is pulled "
                f"(`ollama pull {model}`).]")


def log_history(question: str, answer: str, sources: list[str]):
    """Appends one Q&A record as a JSON line to HISTORY_FILE."""
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "sources": sources,
    }
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[warn] Could not write to history file: {e}")


def show_history(last_n: int | None = None):
    """Prints past Q&A records from HISTORY_FILE."""
    if not os.path.exists(HISTORY_FILE):
        print("No history yet — ask some questions first.")
        return

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    if last_n:
        lines = lines[-last_n:]

    if not lines:
        print("No history yet — ask some questions first.")
        return

    for i, rec in enumerate(lines, 1):
        print(f"\n[{i}] {rec['timestamp']}")
        print(f"Q: {rec['question']}")
        print(f"A: {rec['answer']}")
        if rec.get("sources"):
            print(f"Sources: {', '.join(rec['sources'])}")
    print(f"\n({len(lines)} record(s) shown)")


def answer_question(question: str, top_k: int = TOP_K) -> str:
    chunks = retrieve(question, top_k)
    if not chunks:
        answer = "No documents in the database yet. Add PDFs first with --add."
        log_history(question, answer, [])
        return answer

    prompt = build_prompt(question, chunks)
    answer = ask_ollama(prompt)

    sources_used = sorted({f"{c['source']} (p.{c['page']})" for c in chunks})
    log_history(question, answer, sources_used)

    footer = "\n\nRetrieved from: " + ", ".join(sources_used)
    return answer + footer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def interactive_loop():
    print("=== Multi-PDF RAG — ask questions ('history' to view past Q&A, 'exit' to quit) ===\n")
    while True:
        q = input("Q: ").strip()
        if q.lower() in ("exit", "quit", "q"):
            break
        if not q:
            continue
        if q.lower() == "history":
            show_history()
            print()
            continue
        print("\n" + answer_question(q) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-PDF RAG system")
    parser.add_argument("--add", nargs="+", metavar="PDF", help="PDF file(s) to add to the knowledge base")
    parser.add_argument("--ask", action="store_true", help="Start interactive Q&A session")
    parser.add_argument("--question", type=str, help="Ask a single question and exit")
    parser.add_argument("--history", nargs="?", const=-1, type=int, metavar="N",
                         help="Show past Q&A history (optionally last N entries)")
    args = parser.parse_args()

    if args.add:
        add_pdfs(args.add)

    if args.question:
        print(answer_question(args.question))
    elif args.ask:
        interactive_loop()
    elif args.history is not None:
        show_history(None if args.history == -1 else args.history)

    if not (args.add or args.ask or args.question or args.history is not None):
        parser.print_help()


if __name__ == "__main__":
    main()