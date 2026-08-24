# Multi-PDF RAG System

Ingests multiple PDFs, chunks + embeds them locally, stores in ChromaDB, and
answers your questions by retrieving relevant chunks and summarizing with a
local LLM (Ollama) — no API key, no cost, works offline once set up.

## 1. Install dependencies

```bash
pip install chromadb sentence-transformers pypdf ollama --break-system-packages
```

## 2. Install Ollama (local LLM runner)

- Download: https://ollama.com/download
- Then pull a model:
```bash
ollama pull llama3        # good general model, ~4.7GB
# or a smaller/faster one:
ollama pull phi3
```
Ollama runs a local server automatically after install (`ollama serve` if not).

## 3. Add PDFs to the knowledge base

```bash
python rag_system.py --add report1.pdf report2.pdf notes.pdf
```

This extracts text page-by-page, splits into ~800-char overlapping chunks,
embeds them with `all-MiniLM-L6-v2`, and stores them in a local ChromaDB
folder (`./chroma_db`) — persists across runs.

## 4. Ask questions

Interactive mode:
```bash
python rag_system.py --ask
```

One-off question:
```bash
python rag_system.py --question "What are the main findings in report1?"
```

Each answer cites which PDF + page number the info came from.

## How it works

1. **Extract** — `pypdf` pulls text per page from each PDF.
2. **Chunk** — sliding window (800 chars, 150 overlap) keeps context intact across boundaries.
3. **Embed + Store** — `sentence-transformers` embeds chunks, ChromaDB stores them persistently with metadata (source file, page number).
4. **Retrieve** — on a question, top-5 most similar chunks are pulled via vector similarity.
5. **Answer** — chunks + question are sent to a local LLM (Ollama) which answers using only that context, with citations.

## Customize

Edit the config block at the top of `rag_system.py`:
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — tune for longer/shorter documents
- `TOP_K` — how many chunks to retrieve per question
- `OLLAMA_MODEL` — swap `llama3` for `mistral`, `phi3`, `gemma2`, etc.
- `EMBED_MODEL` — swap for a different sentence-transformers model

## Notes

- Scanned/image-only PDFs won't extract text (no OCR built in) — the script
  will skip them and tell you.
- First run downloads the embedding model (~90MB) from Hugging Face — needs
  internet once, then it's cached locally.
