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
import os
import sys
import uuid
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
CHUNK_SIZE = 800                    # characters per chunk
CHUNK_OVERLAP = 150                 # overlap between chunks
TOP_K = 5                           # chunks retrieved per question
OLLAMA_MODEL = "llama3"             # change to whatever model you've pulled


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


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window character chunker."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
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


def answer_question(question: str, top_k: int = TOP_K) -> str:
    chunks = retrieve(question, top_k)
    if not chunks:
        return "No documents in the database yet. Add PDFs first with --add."

    prompt = build_prompt(question, chunks)
    answer = ask_ollama(prompt)

    sources_used = sorted({f"{c['source']} (p.{c['page']})" for c in chunks})
    footer = "\n\nRetrieved from: " + ", ".join(sources_used)
    return answer + footer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def interactive_loop():
    print("=== Multi-PDF RAG — ask questions (type 'exit' to quit) ===\n")
    while True:
        q = input("Q: ").strip()
        if q.lower() in ("exit", "quit", "q"):
            break
        if not q:
            continue
        print("\n" + answer_question(q) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-PDF RAG system")
    parser.add_argument("--add", nargs="+", metavar="PDF", help="PDF file(s) to add to the knowledge base")
    parser.add_argument("--ask", action="store_true", help="Start interactive Q&A session")
    parser.add_argument("--question", type=str, help="Ask a single question and exit")
    args = parser.parse_args()

    if args.add:
        add_pdfs(args.add)

    if args.question:
        print(answer_question(args.question))
    elif args.ask:
        interactive_loop()

    if not (args.add or args.ask or args.question):
        parser.print_help()


if __name__ == "__main__":
    main()
