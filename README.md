# 🩵 PDFpulse — Multi-PDF RAG System

> Upload PDFs. Ask anything. Get grounded answers with citations — powered by your own local AI. No API keys. No cloud. Fully offline.

---

## ✨ What it does

PDFpulse lets you chat with your PDF documents using a local LLM (Ollama). Upload multiple PDFs, ask questions in plain English, and get accurate answers with source citations (filename + page number). Everything runs on your machine.

---

## 📁 Project Structure

```
PDFpulse/
├── rag_system.py        # Core logic — PDF parsing, chunking, ChromaDB, Ollama
├── server.py            # Flask backend — REST API
├── templates/
│   └── index.html       # Frontend HTML
├── static/
│   ├── style.css        # Custom CSS (colorful/playful theme)
│   └── app.js           # Frontend JavaScript
├── chroma_db/           # Auto-created — vector database (don't delete)
├── history.jsonl        # Auto-created — Q&A log
└── README.md            # You are here
```

---

## ⚙️ Setup (one time)

### 1. Create & activate virtual environment
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

### 3. Install Ollama (local LLM)
Download from 👉 https://ollama.com/download

Then pull a model:
```bash
ollama pull llama3       # recommended (~4.7GB)
# OR smaller/faster:
ollama pull phi3
ollama pull mistral
```

---

## 🚀 Running the app

```bash
python server.py
```

Then open **http://localhost:5000** in your browser.

> **Note:** First time you upload a PDF, the embedding model (~90MB) will be downloaded automatically from HuggingFace. This is a one-time download.

---

## 🖥️ Web UI

| Feature | Description |
|---|---|
| 📤 Drag & Drop Upload | Drop PDFs in the sidebar, click Process |
| 📊 Live Stats | PDFs loaded, chunks indexed, questions asked |
| 📚 Library View | All your uploaded PDFs shown as pills |
| 💬 Chat Interface | Chat bubbles with avatars, smooth animations |
| 📎 Source Preview | Expand to see exact text chunks used for each answer |
| 🕒 History Tab | All past Q&A, click to expand |

---

## 💻 CLI Usage (terminal)

Add PDFs:
```bash
python rag_system.py --add file1.pdf file2.pdf
```

Interactive Q&A session:
```bash
python rag_system.py --ask
```

Single question:
```bash
python rag_system.py --question "What is this document about?"
```

View history:
```bash
python rag_system.py --history        # all
python rag_system.py --history 5      # last 5 only
```

---

## 🔧 Customize

Open `rag_system.py` and edit the config block at the top:

| Setting | Default | What it does |
|---|---|---|
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `TOP_K` | `5` | Chunks retrieved per question |
| `OLLAMA_MODEL` | `llama3` | Swap to `phi3`, `mistral`, `gemma2` etc. |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence embedding model |

---

## ❓ Troubleshooting

**`ModuleNotFoundError`** — Make sure your venv is activated (`(.venv)` in terminal) and run `pip install flask chromadb sentence-transformers pypdf ollama`

**Ollama error** — Make sure Ollama is running. Try `ollama serve` in a separate terminal, and confirm your model is pulled with `ollama list`

**Scanned PDFs not working** — PDFpulse extracts text only. Image-based/scanned PDFs need OCR (not included)

**First upload is slow** — Normal! The embedding model is downloading (~90MB, one time only)

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| PDF parsing | `pypdf` |
| Text chunking | Custom sentence-aware chunker (built-in `re`) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector DB | `ChromaDB` (local, persistent) |
| LLM | `Ollama` (local, any model) |
| Backend | `Flask` |
| Frontend | Vanilla HTML + CSS + JS |

---
