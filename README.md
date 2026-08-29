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

## Web UI (recommended — full custom HTML/CSS/JS, no framework restrictions)

A proper browser-based UI is included: a Flask backend (`server.py`) that
reuses all the logic from `rag_system.py`, plus a hand-built frontend
(`templates/index.html`, `static/style.css`, `static/app.js`) — a real
webpage with drag-and-drop upload, a chat interface, source-chunk previews,
and a history tab.

Install (one extra package):
```bash
pip install flask --break-system-packages
```

Run:
```bash
python server.py
```

Then open **http://localhost:5000** in your browser.

Folder structure needed (already set up if you keep all the provided files together):
```
PDFpulse/
├── rag_system.py
├── server.py
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

What you get:
- **Sidebar** — drag-and-drop PDF upload, live stats (PDFs / chunks / questions), your document library as pills
- **Chat tab** — real chat bubbles with avatars, example question chips, expandable "sources used" under each answer
- **History tab** — click any past question to expand its full answer + sources

The CLI (`rag_system.py`) still works exactly as before if you prefer the terminal.

## CLI usage (terminal)


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

## History

Every question + answer gets logged to `./history.jsonl` (one JSON record
per line, with timestamp + sources used).

View it:
```bash
python rag_system.py --history        # all history
python rag_system.py --history 5      # last 5 entries only
```

Or inside `--ask` mode, just type `history` at the prompt.

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