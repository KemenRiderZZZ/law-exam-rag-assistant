const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const submitBtn = document.getElementById("submit-btn");
const messagesEl = document.getElementById("messages");
const welcomeStateEl = document.getElementById("welcome-state");
const statHealthEl = document.getElementById("stat-health");
const statModelEl = document.getElementById("stat-model");
const statusTextEl = document.getElementById("status-text");
const resultCountEl = document.getElementById("result-count");
const settingsDrawerEl = document.getElementById("settings-drawer");
const openSettingsBtn = document.getElementById("open-settings-btn");
const closeSettingsBtn = document.getElementById("close-settings-btn");
const fillDemoBtn = document.getElementById("fill-demo");
const readerModalEl = document.getElementById("reader-modal");
const readerBookEl = document.getElementById("reader-book");
const readerTitleEl = document.getElementById("reader-title");
const readerMetaEl = document.getElementById("reader-meta");
const readerContentEl = document.getElementById("reader-content");
const closeReaderBtn = document.getElementById("close-reader-btn");

const messages = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatScore(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(4) : "-";
}

function autoResizeTextarea() {
  queryInput.style.height = "auto";
  queryInput.style.height = `${Math.min(queryInput.scrollHeight, 180)}px`;
}

function setStatus(text) {
  statusTextEl.textContent = text;
}

function setDrawerOpen(open) {
  settingsDrawerEl.classList.toggle("open", open);
  settingsDrawerEl.setAttribute("aria-hidden", open ? "false" : "true");
}

function openReader(citation) {
  const title = citation.subsection || citation.section || citation.chapter || citation.book_name || "原文片段";
  const path = [citation.chapter, citation.section, citation.subsection].filter(Boolean).join(" / ");
  readerBookEl.textContent = citation.book_name || "未命名书籍";
  readerTitleEl.textContent = title;
  readerMetaEl.textContent = `chunk_id: ${citation.chunk_id || "-"}  |  行号 ${citation.source_line_start || "-"} - ${citation.source_line_end || "-"}${path ? `  |  ${path}` : ""}`;
  readerContentEl.textContent = citation.text_content || "";
  readerModalEl.hidden = false;
}

function closeReader() {
  readerModalEl.hidden = true;
}

function createUserMessage(text) {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    text,
  };
}

function createAssistantMessage() {
  return {
    id: `assistant-${Date.now() + 1}`,
    role: "assistant",
    status: "loading",
    text: "",
    meta: [],
    citations: [],
    error: "",
  };
}

function renderMessages() {
  if (!messages.length) {
    welcomeStateEl.hidden = false;
    messagesEl.innerHTML = "";
    return;
  }

  welcomeStateEl.hidden = true;

  messagesEl.innerHTML = messages
    .map((message) => {
      if (message.role === "user") {
        return `
          <article class="message-row user">
            <div class="message-card">
              <div class="message-text">${escapeHtml(message.text)}</div>
            </div>
          </article>
        `;
      }

      const statusMap = {
        loading: "正在检索相关法考片段…",
        success: "检索完成",
        error: "检索失败",
      };

      const metaHtml = (message.meta || []).length
        ? `
            <div class="meta-strip">
              ${message.meta.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
            </div>
          `
        : "";

      const citationsHtml = (message.citations || []).length
        ? `
            <section class="citations-block">
              <div class="citations-head">
                <h3>知识引用来源</h3>
                <span>共 ${message.citations.length} 条</span>
              </div>
              ${message.citations
                .map((citation, index) => {
                  const title =
                    citation.subsection ||
                    citation.section ||
                    citation.chapter ||
                    citation.book_name ||
                    `结果 ${index + 1}`;
                  const subtitle = [
                    citation.book_name,
                    [citation.chapter, citation.section, citation.subsection].filter(Boolean).join(" / "),
                    `行号 ${citation.source_line_start || "-"} - ${citation.source_line_end || "-"}`,
                  ]
                    .filter(Boolean)
                    .join(" · ");

                  return `
                    <article class="citation-card">
                      <div class="citation-main">
                        <div class="citation-copy">
                          <h4 class="citation-title">${escapeHtml(title)}</h4>
                          <p class="citation-subtitle">${escapeHtml(subtitle)}</p>
                        </div>
                        <div class="citation-actions">
                          <span class="score-tag">TOP ${index + 1} · ${formatScore(citation.score)}</span>
                          <button class="link-btn" type="button" data-open-citation="${escapeHtml(citation.chunk_id || String(index))}">
                            查看原文
                          </button>
                        </div>
                      </div>
                      <p class="citation-snippet">${escapeHtml(citation.text_content || "")}</p>
                    </article>
                  `;
                })
                .join("")}
            </section>
          `
        : "";

      const errorHtml = message.error
        ? `<div class="message-text">${escapeHtml(message.error)}</div>`
        : `<div class="message-text">${escapeHtml(message.text)}</div>`;

      return `
        <article class="message-row assistant">
          <div class="message-card">
            <div class="assistant-stack">
              <div class="message-status ${escapeHtml(message.status)}">${escapeHtml(statusMap[message.status] || "处理中")}</div>
              ${errorHtml}
              ${metaHtml}
              ${citationsHtml}
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  messagesEl.querySelectorAll("[data-open-citation]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.getAttribute("data-open-citation");
      const assistant = [...messages]
        .reverse()
        .find((message) => message.role === "assistant" && (message.citations || []).some((citation, index) => (citation.chunk_id || String(index)) === key));
      if (!assistant) return;

      const citation =
        assistant.citations.find((item) => item.chunk_id === key) ||
        assistant.citations[Number(key)] ||
        assistant.citations[0];
      if (citation) openReader(citation);
    });
  });

  messagesEl.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("health failed");
    statHealthEl.textContent = "连接稳定";
  } catch {
    statHealthEl.textContent = "无法访问";
  }
}

function buildAssistantSummary(payload, query) {
  const count = (payload.results || []).length;
  if (!count) {
    return `没有检索到与“${query}”直接相关的片段。你可以尝试更换问法，或者放宽书名、章节筛选条件。`;
  }

  return `已为“${query}”检索到 ${count} 条相关片段。下面先给出命中的法考原文，你可以继续追问，我再根据这些片段继续帮你整理重点。`;
}

async function handleSearch(event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  const userMessage = createUserMessage(query);
  const assistantMessage = createAssistantMessage();
  messages.push(userMessage, assistantMessage);
  renderMessages();

  submitBtn.disabled = true;
  setStatus("正在生成查询向量并检索本地向量库");
  resultCountEl.textContent = "检索中…";

  const payload = {
    query,
    top_k: Number(form.top_k.value || 5),
    book_name: form.book_name.value.trim(),
    chapter: form.chapter.value.trim(),
    no_model_filter: form.no_model_filter.checked,
  };

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "检索失败");
    }

    statModelEl.textContent = data.embedding_model || "BAAI/bge-m3";

    assistantMessage.status = "success";
    assistantMessage.text = buildAssistantSummary(data, query);
    assistantMessage.meta = [
      `检索模型：${data.embedding_model || "BAAI/bge-m3"}`,
      `Top K：${payload.top_k}`,
      `命中数量：${(data.results || []).length}`,
      `驱动：${data.driver || "-"}`,
    ];
    assistantMessage.citations = data.results || [];

    const usageText = data.usage ? `；embedding 用量 ${JSON.stringify(data.usage)}` : "";
    setStatus(`检索完成${usageText}`);
    resultCountEl.textContent = `命中 ${(data.results || []).length} 条`;
  } catch (error) {
    assistantMessage.status = "error";
    assistantMessage.error = error.message || "系统异常";
    setStatus("检索失败");
    resultCountEl.textContent = "发生错误";
  } finally {
    renderMessages();
    submitBtn.disabled = false;
    queryInput.value = "";
    autoResizeTextarea();
  }
}

queryInput.addEventListener("input", autoResizeTextarea);

queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", handleSearch);

fillDemoBtn.addEventListener("click", () => {
  queryInput.value = "侵犯公民个人信息罪怎么认定？";
  form.book_name.value = "";
  form.chapter.value = "";
  form.top_k.value = "5";
  form.no_model_filter.checked = false;
  autoResizeTextarea();
  queryInput.focus();
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.getAttribute("data-question") || "";
    autoResizeTextarea();
    queryInput.focus();
  });
});

openSettingsBtn.addEventListener("click", () => setDrawerOpen(true));
closeSettingsBtn.addEventListener("click", () => setDrawerOpen(false));
settingsDrawerEl.addEventListener("click", (event) => {
  if (event.target === settingsDrawerEl) setDrawerOpen(false);
});

closeReaderBtn.addEventListener("click", closeReader);
readerModalEl.querySelector(".reader-mask").addEventListener("click", closeReader);

checkHealth();
autoResizeTextarea();
