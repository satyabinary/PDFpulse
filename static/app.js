// ============================================================
// PDFpulse — Frontend Logic
// ============================================================

const state = { pendingFiles: [] };

// ---------- Elements ----------
const dropzone       = document.getElementById("dropzone");
const fileInput      = document.getElementById("fileInput");
const fileListEl     = document.getElementById("fileList");
const processBtn     = document.getElementById("processBtn");
const uploadStatus   = document.getElementById("uploadStatus");
const libraryPills   = document.getElementById("libraryPills");
const statPdfs       = document.getElementById("statPdfs");
const statChunks     = document.getElementById("statChunks");
const statQuestions  = document.getElementById("statQuestions");
const chatEmpty      = document.getElementById("chatEmpty");
const chatMessages   = document.getElementById("chatMessages");
const chatForm       = document.getElementById("chatForm");
const chatInput      = document.getElementById("chatInput");
const clearChatBtn   = document.getElementById("clearChatBtn");
const chatToolbar    = document.getElementById("chatToolbar");
const exportTxt      = document.getElementById("exportTxt");
const exportPdf      = document.getElementById("exportPdf");
const historyList    = document.getElementById("historyList");
const historySearch  = document.getElementById("historySearch");
const historySearchBtn   = document.getElementById("historySearchBtn");
const historyClearSearch = document.getElementById("historyClearSearch");
const historySearchInfo  = document.getElementById("historySearchInfo");
const statusDot  = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// ============================================================
// Status indicator (top right)
// ============================================================
const SARCASTIC_IDLE = [
  "idle — waiting for you",
  "staring into the void",
  "ready. are you?",
  "doing absolutely nothing",
  "standing by, as always",
];

function setStatus(state, text) {
  statusDot.className = "status-dot" + (state ? ` ${state}` : "");
  statusText.textContent = text;
}

function setIdleStatus() {
  const msg = SARCASTIC_IDLE[Math.floor(Math.random() * SARCASTIC_IDLE.length)];
  setStatus("", msg);
}

setIdleStatus();

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
// File upload — drag & drop + browse
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
  fileInput.value = "";
});

function addFiles(fileListObj) {
  for (const f of fileListObj) {
    if (f.name.toLowerCase().endsWith(".pdf")) {
      // no duplicates
      if (!state.pendingFiles.find(x => x.name === f.name)) {
        state.pendingFiles.push(f);
      }
    }
  }
  renderFileList();
}

function renderFileList() {
  fileListEl.innerHTML = "";
  state.pendingFiles.forEach((f, idx) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>◈ ${escapeHtml(f.name)}</span><span class="remove" data-idx="${idx}">✕</span>`;
    fileListEl.appendChild(li);
  });
  fileListEl.querySelectorAll(".remove").forEach(el => {
    el.addEventListener("click", (e) => {
      state.pendingFiles.splice(parseInt(e.target.dataset.idx, 10), 1);
      renderFileList();
    });
  });
  processBtn.disabled = state.pendingFiles.length === 0;
}

// ============================================================
// Process PDFs
// ============================================================
const SARCASTIC_UPLOAD = [
  "fine, i'll read it",
  "indexing your docs...",
  "chunking away...",
  "embedding... this takes a sec",
  "please hold. or don't. i'll finish either way.",
];

processBtn.addEventListener("click", async () => {
  if (!state.pendingFiles.length) return;

  processBtn.disabled = true;
  const msg = SARCASTIC_UPLOAD[Math.floor(Math.random() * SARCASTIC_UPLOAD.length)];
  setStatus("active", "processing...");
  uploadStatus.textContent = `⟳ ${msg}`;
  uploadStatus.className = "status-msg loading";

  const formData = new FormData();
  state.pendingFiles.forEach(f => formData.append("files", f));

  try {
    const res  = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "upload failed");

    uploadStatus.textContent = `✓ indexed ${data.processed.length} file(s) — ${data.chunk_count} chunks total`;
    uploadStatus.className = "status-msg success";
    state.pendingFiles = [];
    renderFileList();
    refreshStatus();
    setStatus("ready", "docs loaded");
  } catch (err) {
    uploadStatus.textContent = `✗ ${err.message}`;
    uploadStatus.className = "status-msg error";
    processBtn.disabled = false;
    setIdleStatus();
  }
});

// ============================================================
// Stats & library
// ============================================================
async function refreshStatus() {
  try {
    const res  = await fetch("/api/status");
    const data = await res.json();

    statPdfs.textContent      = data.pdf_count;
    statChunks.textContent    = data.chunk_count;
    statQuestions.textContent = data.question_count;

    if (data.sources && data.sources.length > 0) {
      libraryPills.innerHTML = data.sources
        .map(s => `<span class="pill">◈ ${escapeHtml(s)}</span>`)
        .join("");
      setStatus("ready", `${data.pdf_count} doc(s) loaded`);
    } else {
      libraryPills.innerHTML = `<span class="empty-hint">nothing here yet. upload something.</span>`;
      setIdleStatus();
    }
  } catch (err) {
    console.error("status fetch failed", err);
  }
}

// ============================================================
// Chat — example chips
// ============================================================
document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    chatInput.value = chip.dataset.q;
    chatForm.dispatchEvent(new Event("submit"));
  });
});

// ============================================================
// Chat — send message
// ============================================================
const SARCASTIC_THINKING = [
  "hold on, actually reading this...",
  "consulting the void...",
  "processing. patience is a virtue.",
  "cross-referencing your docs...",
  "thinking... unlike some people.",
];

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = chatInput.value.trim();
  if (!question) return;

  chatEmpty.style.display  = "none";
  chatToolbar.style.display = "flex";
  addMessage("user", question);
  chatInput.value = "";

  const thinkingMsg = SARCASTIC_THINKING[Math.floor(Math.random() * SARCASTIC_THINKING.length)];
  setStatus("active", "thinking...");
  const thinkingEl = addMessage("assistant", thinkingMsg, { thinking: true });

  try {
    const res  = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "something went wrong");

    updateMessage(thinkingEl, data.answer, data.chunks || []);
    refreshStatus();
    setStatus("ready", "answered");
    setTimeout(setIdleStatus, 3000);
  } catch (err) {
    updateMessage(thinkingEl, `✗ ${err.message}`, []);
    setStatus("", "error");
    setTimeout(setIdleStatus, 3000);
  }
});

function addMessage(role, text, opts = {}) {
  const msg    = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "you" : "ai";

  const wrap   = document.createElement("div");
  wrap.className = "bubble-wrap";

  const bubble = document.createElement("div");
  bubble.className = "bubble" + (opts.thinking ? " thinking" : "");

  if (opts.thinking) {
    bubble.innerHTML = `${escapeHtml(text)} <span class="thinking-dots"></span>`;
  } else {
    bubble.textContent = text;
  }

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
    toggle.innerHTML = `<span>▸</span> ${chunks.length} source(s) used`;

    const box = document.createElement("div");
    box.className = "sources-box";
    box.innerHTML = chunks.map(c => `
      <div class="source-chunk">
        <div class="meta">◈ ${escapeHtml(c.source)} · p.${c.page}</div>
        ${escapeHtml(c.text.slice(0, 380))}${c.text.length > 380 ? "..." : ""}
      </div>
    `).join("");

    toggle.addEventListener("click", () => {
      const open = box.classList.toggle("open");
      toggle.querySelector("span").textContent = open ? "▾" : "▸";
    });

    msgRef.wrap.appendChild(toggle);
    msgRef.wrap.appendChild(box);
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================================
// Clear chat
// ============================================================
clearChatBtn.addEventListener("click", () => {
  chatMessages.innerHTML   = "";
  chatEmpty.style.display  = "flex";
  chatToolbar.style.display = "none";
  setIdleStatus();
});

// ============================================================
// Export — text file
// ============================================================
exportTxt.addEventListener("click", () => {
  const messages = chatMessages.querySelectorAll(".msg");
  if (!messages.length) return;

  const lines = [
    `PDFpulse — Chat Export`,
    `Generated: ${new Date().toLocaleString()}`,
    `${"─".repeat(50)}`,
    "",
  ];

  messages.forEach(msg => {
    const role   = msg.classList.contains("user") ? "YOU" : "PDFPULSE";
    const text   = msg.querySelector(".bubble")?.textContent?.trim() || "";
    lines.push(`[${role}]\n${text}\n`);

    msg.querySelectorAll(".source-chunk").forEach(c => {
      const meta = c.querySelector(".meta")?.textContent?.trim() || "";
      const body = c.textContent.replace(meta, "").trim();
      lines.push(`  source: ${meta}\n  ${body.slice(0, 200)}...\n`);
    });
  });

  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `pdfpulse-${new Date().toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
});

// Export — PDF via browser print
exportPdf.addEventListener("click", () => window.print());

// ============================================================
// History
// ============================================================
async function loadHistory(query = "") {
  try {
    const url  = query
      ? `/api/history/search?q=${encodeURIComponent(query)}`
      : "/api/history";
    const res  = await fetch(url);
    const data = await res.json();
    const records = query ? data.results : data.history;

    if (query) {
      historySearchInfo.innerHTML = records.length
        ? `found <span class="highlight">${records.length}</span> result(s) for "<span class="highlight">${escapeHtml(query)}</span>"`
        : `nothing found for "<span class="highlight">${escapeHtml(query)}</span>" — try another keyword`;
      historyClearSearch.style.display = "inline-flex";
    } else {
      historySearchInfo.innerHTML = records && records.length
        ? `<span class="highlight">${records.length}</span> total queries on record`
        : "";
      historyClearSearch.style.display = "none";
    }

    if (!records || !records.length) {
      historyList.innerHTML = query
        ? `<p class="empty-hint">no matches. are you sure you asked that?</p>`
        : `<p class="empty-hint">no history yet. start a conversation.</p>`;
      return;
    }

    historyList.innerHTML = records.map(rec => `
      <div class="history-item">
        <div class="h-question">${escapeHtml(rec.question)}</div>
        <div class="h-time">${escapeHtml(rec.timestamp)}</div>
        <div class="h-answer">${escapeHtml(rec.answer)}</div>
        <div class="h-sources">
          ${(rec.sources || []).map(s => `<span class="pill">${escapeHtml(s)}</span>`).join("")}
        </div>
      </div>
    `).join("");

    historyList.querySelectorAll(".history-item").forEach(item => {
      item.addEventListener("click", () => item.classList.toggle("open"));
    });
  } catch (err) {
    historyList.innerHTML = `<p class="empty-hint">failed to load history. classic.</p>`;
  }
}

historySearchBtn.addEventListener("click",  () => loadHistory(historySearch.value.trim()));
historySearch.addEventListener("keydown", e => { if (e.key === "Enter") loadHistory(historySearch.value.trim()); });
historyClearSearch.addEventListener("click", () => {
  historySearch.value = "";
  historyClearSearch.style.display = "none";
  historySearchInfo.innerHTML = "";
  loadHistory();
});

// ============================================================
// Utils
// ============================================================
function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ============================================================
// Init
// ============================================================
refreshStatus();