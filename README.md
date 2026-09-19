# ⚡ PDFpulse — Multi-PDF RAG System

> reads your boring PDFs so you don't have to.

Local AI. No cloud. No API keys. No subscription. Just upload, ask, get answers.

---

## 📁 Project Structure

```
PDFpulse/
├── rag_system.py        # Core — PDF parsing, chunking, ChromaDB, Ollama
├── server.py            # Flask backend — REST API
├── templates/
│   └── index.html       # Frontend HTML
├── static/
│   ├── style.css        # Dark theme — purple + cyan
│   └── app.js           # Frontend JS
├── chroma_db/           # Auto-created — vector DB (don't touch)
├── history.jsonl        # Auto-created — Q&A log
└── README.md            # you are here
```

---

## ⚙️ Setup

### 1. Virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install flask chromadb sentence-transformers pypdf ollama
```

### 3. Install Ollama
Download → https://ollama.com/download

```bash
ollama pull llama3       # ~4.7GB, recommended
# OR lighter options:
ollama pull phi3
ollama pull mistral
```

---

## 🚀 Run

```bash
python server.py
```

Open **http://localhost:5000** in browser.

> First upload will download the embedding model (~90MB). One time only.

---

## 🖥️ Web UI Features

| Feature | What it does |
|---|---|
| ⚡ Drag & Drop | Drop PDFs in sidebar, hit Process & Index |
| ◈ Live Stats | PDFs / chunks / queries — updates in real time |
| ◉ Chat | Dark terminal-style chat with sarcastic status messages |
| ▸ Source Preview | Expand to see exact chunks used per answer |
| ↓ Export | Download chat as `.txt` or `.pdf` |
| ⌕ History Search | Search past Q&A by keyword (AND logic) |

---

## 💻 CLI Usage

```bash
# Add PDFs
python rag_system.py --add file1.pdf file2.pdf

# Interactive Q&A
python rag_system.py --ask

# Single question
python rag_system.py --question "what is this about?"

# View history
python rag_system.py --history
python rag_system.py --history 5        # last 5 only

# Search history
python rag_system.py --search-history "machine learning"
```

---

## 🔧 Config

Edit top of `rag_system.py`:

| Variable | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `TOP_K` | `5` | Chunks retrieved per question |
| `OLLAMA_MODEL` | `llama3` | Swap to `phi3`, `mistral`, `gemma2` |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Embedding model |

---

## ❌ Common Errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Activate venv → `pip install flask chromadb sentence-transformers pypdf ollama` |
| `No module named 'chromadb'` | `pip install chromadb` inside venv |
| Ollama error | Run `ollama serve` in separate terminal, check `ollama list` |
| Scanned PDF not working | PDFpulse reads text only — scanned/image PDFs need OCR (not included) |
| First upload slow | Normal — embedding model downloading (~90MB, once) |

---

## 🛠️ Stack

| Layer | Tech |
|---|---|
| PDF parsing | `pypdf` |
| Chunking | Custom sentence-aware (built-in `re`) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Vector DB | `ChromaDB` (local, persistent) |
| LLM | `Ollama` (fully local) |
| Backend | `Flask` |
| Frontend | Vanilla HTML + CSS + JS (dark theme, no framework) |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Web UI |
| GET | `/api/status` | Stats — pdf count, chunks, sources |
| POST | `/api/upload` | Upload PDFs (multipart `files`) |
| POST | `/api/ask` | Ask question (`{"question": "..."}`) |
| GET | `/api/history` | All past Q&A |
| GET | `/api/history/search?q=keyword` | Search history |

---
