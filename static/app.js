// ============================================================
// PDFpulse frontend logic — talks to the Flask API (/api/...)
// ============================================================

const state = {
  pendingFiles: [],
};

// ---------- Elements ----------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileListEl = document.getElementById("fileList");
const processBtn = document.getElementById("processBtn");
const uploadStatus = document.getElementById("uploadStatus");
const libraryPills = document.getElementById("libraryPills");
const statPdfs = document.getElementById("statPdfs");
const statChunks = document.getElementById("statChunks");
const statQuestions = document.getElementById("statQuestions");

const chatEmpty = document.getElementById("chatEmpty");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const clearChatBtn = document.getElementById("clearChatBtn");

const historyList = document.getElementById("historyList");

// ============================================================
// Tabs
// ============================================================
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "history") loadHistory();
  });
});

// ============================================================
// File upload (drag & drop + browse)
// ============================================================
dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  addFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", () => {
  addFiles(fileInput.files);
  fileInput.value = ""; // allow re-selecting the same file
});

function addFiles(fileListObj) {
  for (const f of fileListObj) {
    if (f.name.toLowerCase().endsWith(".pdf")) {
      state.pendingFiles.push(f);
    }
  }
  renderFileList();
}

function renderFileList() {
  fileListEl.innerHTML = "";
  state.pendingFiles.forEach((f, idx) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>📄 ${f.name}</span><span class="remove" data-idx="${idx}">✕</span>`;
    fileListEl.appendChild(li);
  });
  fileListEl.querySelectorAll(".remove").forEach(el => {
    el.addEventListener("click", (e) => {
      const idx = parseInt(e.target.dataset.idx, 10);
      state.pendingFiles.splice(idx, 1);
      renderFileList();
    });
  });
  processBtn.disabled = state.pendingFiles.length === 0;
}

processBtn.addEventListener("click", async () => {
  if (state.pendingFiles.length === 0) return;

  processBtn.disabled = true;
  uploadStatus.textContent = `🔮 Processing ${state.pendingFiles.length} file(s)... this can take a bit on first run.`;
  uploadStatus.className = "status-msg loading";

  const formData = new FormData();
  state.pendingFiles.forEach(f => formData.append("files", f));

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || "Upload failed");

    uploadStatus.textContent = `✅ Added ${data.processed.length} file(s) — ${data.chunk_count} chunks indexed.`;
    uploadStatus.className = "status-msg success";
    state.pendingFiles = [];
    renderFileList();
    refreshStatus();
  } catch (err) {
    uploadStatus.textContent = `❌ ${err.message}`;
    uploadStatus.className = "status-msg error";
    processBtn.disabled = false;
  }
});

// ============================================================
// Status / stats / library
// ============================================================
async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    statPdfs.textContent = data.pdf_count;
    statChunks.textContent = data.chunk_count;
    statQuestions.textContent = data.question_count;

    if (data.sources && data.sources.length > 0) {
      libraryPills.innerHTML = data.sources.map(s => `<span class="pill">📄 ${escapeHtml(s)}</span>`).join("");
    } else {
      libraryPills.innerHTML = `<span class="empty-hint">No PDFs yet</span>`;
    }
  } catch (err) {
    console.error("Failed to refresh status", err);
  }
}

// ============================================================
// Chat
// ============================================================
document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    chatInput.value = chip.dataset.q;
    chatForm.dispatchEvent(new Event("submit"));
  });
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = chatInput.value.trim();
  if (!question) return;

  chatEmpty.style.display = "none";
  addMessage("user", question);
  chatInput.value = "";

  const thinkingEl = addMessage("assistant", "Thinking...", { thinking: true });

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong");

    updateMessage(thinkingEl, data.answer, data.chunks || []);
    refreshStatus();
  } catch (err) {
    updateMessage(thinkingEl, `❌ ${err.message}`, []);
  }
});

function addMessage(role, text, opts = {}) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "🙋" : "🩵";

  const bubble = document.createElement("div");
  bubble.className = "bubble" + (opts.thinking ? " thinking" : "");
  bubble.textContent = text;

  const wrap = document.createElement("div");
  wrap.appendChild(bubble);
  msg.appendChild(avatar);
  msg.appendChild(wrap);

  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return { msg, bubble, wrap };
}

function updateMessage(msgRef, text, chunks) {
  msgRef.bubble.classList.remove("thinking");
  msgRef.bubble.textContent = text;

  if (chunks && chunks.length > 0) {
    const toggle = document.createElement("div");
    toggle.className = "sources-toggle";
    toggle.textContent = `📎 View ${chunks.length} source(s) used ▾`;

    const box = document.createElement("div");
    box.className = "sources-box";
    box.innerHTML = chunks.map(c => `
      <div class="source-chunk">
        <div class="meta">📄 ${escapeHtml(c.source)} · page ${c.page}</div>
        ${escapeHtml(c.text.slice(0, 400))}${c.text.length > 400 ? "..." : ""}
      </div>
    `).join("");

    toggle.addEventListener("click", () => box.classList.toggle("open"));

    msgRef.wrap.appendChild(toggle);
    msgRef.wrap.appendChild(box);
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

clearChatBtn.addEventListener("click", () => {
  chatMessages.innerHTML = "";
  chatEmpty.style.display = "flex";
});

// ============================================================
// History
// ============================================================
const historySearchInput = document.getElementById("historySearch");
const historySearchBtn = document.getElementById("historySearchBtn");
const historyClearSearch = document.getElementById("historyClearSearch");
const historySearchInfo = document.getElementById("historySearchInfo");

async function loadHistory(query = "") {
  try {
    let url = "/api/history";
    if (query) url = `/api/history/search?q=${encodeURIComponent(query)}`;

    const res = await fetch(url);
    const data = await res.json();

    const records = query ? data.results : data.history;

    // Update info bar
    if (query) {
      historySearchInfo.innerHTML = records.length > 0
        ? `Found <span class="highlight">${records.length}</span> result(s) for "<span class="highlight">${escapeHtml(query)}</span>"`
        : `No results found for "<span class="highlight">${escapeHtml(query)}</span>"`;
      historyClearSearch.style.display = "inline-block";
    } else {
      historySearchInfo.innerHTML = records && records.length > 0
        ? `<span class="highlight">${records.length}</span> total Q&A recorded`
        : "";
      historyClearSearch.style.display = "none";
    }

    if (!records || records.length === 0) {
      historyList.innerHTML = query
        ? `<p class="empty-hint">No matching history found — try a different keyword.</p>`
        : `<p class="empty-hint">No history yet — ask a question in the Chat tab first.</p>`;
      return;
    }

    historyList.innerHTML = records.map(rec => `
      <div class="history-item">
        <div class="h-question">🗨️ ${escapeHtml(rec.question)}</div>
        <div class="h-time">${escapeHtml(rec.timestamp)}</div>
        <div class="h-answer">${escapeHtml(rec.answer)}</div>
        <div class="h-sources">${(rec.sources || []).map(s => `<span class="pill">📄 ${escapeHtml(s)}</span>`).join("")}</div>
      </div>
    `).join("");

    historyList.querySelectorAll(".history-item").forEach(item => {
      item.addEventListener("click", () => item.classList.toggle("open"));
    });
  } catch (err) {
    historyList.innerHTML = `<p class="empty-hint">Failed to load history.</p>`;
  }
}

historySearchBtn.addEventListener("click", () => {
  const q = historySearchInput.value.trim();
  loadHistory(q);
});

historySearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const q = historySearchInput.value.trim();
    loadHistory(q);
  }
});

historyClearSearch.addEventListener("click", () => {
  historySearchInput.value = "";
  historyClearSearch.style.display = "none";
  historySearchInfo.innerHTML = "";
  loadHistory();
});

// ============================================================
// Utils
// ============================================================
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ============================================================
// Init
// ============================================================
refreshStatus();