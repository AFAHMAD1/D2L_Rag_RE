// ============================================================
// Ask D2L - chat frontend
// Sections: config · DOM refs · state · storage · helpers · theme ·
//           markdown & math · message rendering · typing animation ·
//           sending questions · sidebar · init
// ============================================================

// ---------- Config ----------

const STORAGE_KEY = "ask-d2l-chats";
const THEME_KEY = "ask-d2l-theme";
const WORD_DELAY_MS = 25;
const MOBILE_QUERY = window.matchMedia("(max-width: 760px)");
const HLJS_DARK = "https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css";
const HLJS_LIGHT = "https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.min.css";

const CHAPTER_SHORT_NAMES = {
  "Preliminaries": "Prelim",
  "Multilayer Perceptrons": "MLP",
  "Convolutional Neural Networks": "CNN",
  "Optimization Algorithms": "Optim",
};

const EXAMPLES = [
  { chapter: "Preliminaries", question: "What is broadcasting in tensors?" },
  { chapter: "Multilayer Perceptrons", question: "Why does dropout help prevent overfitting?" },
  { chapter: "Convolutional Neural Networks", question: "What does a pooling layer do in a CNN?" },
  { chapter: "Optimization Algorithms", question: "How does momentum improve gradient descent?" },
];

const ICON_SPARK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/></svg>`;
const ICON_SUN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`;
const ICON_MOON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>`;

// marked: treat single newlines as line breaks, as chat messages expect.
marked.setOptions({ gfm: true, breaks: true });

// ---------- DOM references ----------

const $ = (id) => document.getElementById(id);
const sidebar = $("sidebar");
const backdrop = $("backdrop");
const chatList = $("chat-list");
const chatScroll = $("chat-scroll");
const messagesEl = $("messages");
const emptyState = $("empty-state");
const cardsEl = $("cards");
const form = $("ask-form");
const input = $("question");
const sendBtn = $("send-btn");
const newChatBtn = $("new-chat");
const menuBtn = $("menu-btn");
const themeBtn = $("theme-btn");
const hljsTheme = $("hljs-theme");

// ---------- State ----------

// Each chat: { id, title, messages: [{ role, content, sources? }] }
let chats = loadChats();
let activeChatId = null; // null means the empty "new chat" screen
let busy = false;        // true while a question is waiting for an answer

// ---------- Storage ----------

function loadChats() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveChats() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch {
    // Storage can be full or blocked; chats still work for this page session.
  }
}

// ---------- Small helpers ----------

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

const truncate = (text, max) => (text.length > max ? text.slice(0, max - 1) + "…" : text);

const currentChat = () => chats.find((c) => c.id === activeChatId) || null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function copyText(text, button, idleLabel) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      button.textContent = "Copied!";
      setTimeout(() => (button.textContent = idleLabel), 1500);
    })
    .catch(() => {
      button.textContent = "Copy failed";
      setTimeout(() => (button.textContent = idleLabel), 1500);
    });
}

// ---------- Theme ----------

// Dark is the default; the choice is remembered in localStorage.
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  hljsTheme.href = theme === "light" ? HLJS_LIGHT : HLJS_DARK;
  themeBtn.innerHTML = theme === "light" ? ICON_MOON : ICON_SUN;
}

themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    // Theme still switches for this visit.
  }
  applyTheme(next);
});

// ---------- Markdown and math ----------

// LaTeX delimiters the model emits: \( ... \) inline and \[ ... \] display.
const MATH_PATTERN = /\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)/g;

// Math is swapped for plain placeholders before Markdown runs, so the Markdown
// parser cannot touch the LaTeX backslashes. KaTeX output is inserted afterwards.
function renderMarkdown(text) {
  const maths = [];
  const withPlaceholders = text.replace(MATH_PATTERN, (_, display, inline) => {
    maths.push({ latex: display ?? inline, displayMode: display !== undefined });
    return `MATHPLACEHOLDER${maths.length - 1}X`;
  });

  const html = DOMPurify.sanitize(marked.parse(withPlaceholders));

  return html.replace(/MATHPLACEHOLDER(\d+)X/g, (_, index) => {
    const { latex, displayMode } = maths[Number(index)];
    return katex.renderToString(latex, { displayMode, throwOnError: false });
  });
}

// Wraps each <pre> in a header (language label + copy button) and highlights it.
function enhanceCodeBlocks(container) {
  container.querySelectorAll("pre").forEach((pre) => {
    const code = pre.querySelector("code");
    if (!code) return;

    const language = (code.className.match(/language-(\S+)/) || [])[1] || "code";
    hljs.highlightElement(code);

    const wrapper = el("div", "code-block");
    const header = el("div", "code-header");
    const copyBtn = el("button", "copy-btn", "Copy");
    copyBtn.type = "button";
    copyBtn.addEventListener("click", () => copyText(code.textContent, copyBtn, "Copy"));

    header.append(el("span", null, language), copyBtn);
    pre.replaceWith(wrapper);
    wrapper.append(header, pre);
  });
}

function renderAnswerInto(target, text) {
  target.innerHTML = renderMarkdown(text);
  enhanceCodeBlocks(target);
}

// ---------- Message rendering ----------

function buildUserMessage(text) {
  const row = el("div", "msg msg-user");
  row.append(el("div", "bubble", text));
  return row;
}

function buildAvatar() {
  const avatar = el("div", "avatar");
  avatar.innerHTML = ICON_SPARK;
  return avatar;
}

// Source chips toggle a panel with the retrieved chunk text.
function buildSources(sources) {
  const wrap = el("div", "sources-wrap");
  const chips = el("div", "sources");
  const panels = el("div", "panels");

  sources.forEach((source) => {
    const short = CHAPTER_SHORT_NAMES[source.chapter] || source.chapter;
    const chip = el("button", "chip", `${short} · p.${source.page}`);
    chip.type = "button";
    chip.title = `${source.chapter}, distance ${source.distance}`;

    const panel = el("div", "chunk-panel", source.text);
    chip.addEventListener("click", () => {
      const open = panel.classList.toggle("open");
      chip.classList.toggle("active", open);
    });

    chips.append(chip);
    panels.append(panel);
  });

  wrap.append(chips, panels);
  return wrap;
}

function buildActions(content) {
  const row = el("div", "actions");
  const copyBtn = el("button", "text-btn", "Copy answer");
  copyBtn.type = "button";
  copyBtn.addEventListener("click", () => copyText(content, copyBtn, "Copy answer"));
  row.append(copyBtn);
  return row;
}

// Assistant messages have no bubble; sources and actions appear after typing ends.
function buildAssistantMessage(message, animate) {
  const row = el("div", "msg msg-assistant");
  const body = el("div", "assistant-body");
  const answer = el("div", message.error ? "answer error" : "answer");
  body.append(answer);
  row.append(buildAvatar(), body);

  if (message.error) {
    answer.textContent = message.content;
    return row;
  }

  const extras = [];
  if (message.sources && message.sources.length) extras.push(buildSources(message.sources));
  extras.push(buildActions(message.content));

  if (animate) {
    extras.forEach((node) => (node.hidden = true));
    body.append(...extras);
    typeOut(answer, message.content, () => {
      renderAnswerInto(answer, message.content);
      extras.forEach((node) => (node.hidden = false));
    });
  } else {
    renderAnswerInto(answer, message.content);
    body.append(...extras);
  }
  return row;
}

function buildThinking() {
  const row = el("div", "msg msg-assistant thinking");
  const body = el("div", "assistant-body");
  body.innerHTML = `<span class="dots"><i></i><i></i><i></i></span>`;
  row.append(buildAvatar(), body);
  return row;
}

function appendMessage(message, animate) {
  const node =
    message.role === "user"
      ? buildUserMessage(message.content)
      : buildAssistantMessage(message, animate);
  messagesEl.append(node);
  scrollToBottom();
  return node;
}

// ---------- Typing animation ----------

// Reveals the answer one word at a time. Each step re-renders the text so far,
// so Markdown and math stay correct while the answer grows.
function typeOut(target, text, onDone) {
  const words = text.match(/\S+\s*/g) || [];
  let shown = 0;

  const step = () => {
    shown += 1;
    renderAnswerInto(target, words.slice(0, shown).join(""));
    scrollToBottom();
    if (shown < words.length) {
      setTimeout(step, WORD_DELAY_MS);
    } else {
      onDone();
    }
  };

  if (words.length) {
    step();
  } else {
    onDone();
  }
}

// ---------- Rendering the whole view ----------

function renderChat() {
  const chat = currentChat();
  messagesEl.replaceChildren();
  (chat ? chat.messages : []).forEach((message) => appendMessage(message, false));
  emptyState.hidden = Boolean(chat && chat.messages.length);
  scrollToBottom();
}

function renderSidebar() {
  chatList.replaceChildren();
  chats.forEach((chat) => {
    const className = chat.id === activeChatId ? "chat-item active" : "chat-item";
    const item = el("button", className, chat.title);
    item.type = "button";
    item.title = chat.title;
    item.addEventListener("click", () => openChat(chat.id));
    chatList.append(item);
  });
}

function openChat(id) {
  activeChatId = id;
  renderChat();
  renderSidebar();
  closeMobileSidebar();
}

// ---------- Sending questions ----------

// Calls the backend and returns the parsed response, or throws an Error with a readable message.
async function askApi(question) {
  let response;
  try {
    response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch {
    throw new Error("Could not reach the server. Is the API running?");
  }

  let data = {};
  try {
    data = await response.json();
  } catch {
    // Non-JSON error bodies fall through to the status-code message below.
  }

  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : null;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}

function setBusy(isBusy) {
  input.disabled = isBusy;
  sendBtn.disabled = isBusy;
  if (!isBusy) input.focus();
}

async function sendQuestion(rawText) {
  const question = rawText.trim();
  if (!question || busy) return;

  busy = true;
  setBusy(true);

  // The first question in a new chat creates the chat; empty chats never appear in the list.
  let chat = currentChat();
  if (!chat) {
    chat = { id: uid(), title: truncate(question, 40), messages: [] };
    chats.unshift(chat);
    activeChatId = chat.id;
  }

  const userMessage = { role: "user", content: question };
  chat.messages.push(userMessage);
  saveChats();
  renderSidebar();

  emptyState.hidden = true;
  appendMessage(userMessage, false);
  input.value = "";
  autosize();

  const thinking = buildThinking();
  messagesEl.append(thinking);
  scrollToBottom();

  try {
    const data = await askApi(question);
    thinking.remove();

    const assistantMessage = { role: "assistant", content: data.answer, sources: data.sources };
    chat.messages.push(assistantMessage);
    saveChats();

    // If the user switched chats while waiting, the answer is saved and shows when they return.
    if (activeChatId === chat.id) appendMessage(assistantMessage, true);
  } catch (err) {
    thinking.remove();
    if (activeChatId === chat.id) {
      appendMessage({ role: "assistant", content: err.message, error: true }, false);
    }
  } finally {
    busy = false;
    setBusy(false);
  }
}

// Grows the textarea with its content, up to the CSS max-height.
function autosize() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendQuestion(input.value);
});

// Enter sends; Shift+Enter inserts a new line.
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener("input", autosize);

// ---------- Example cards on the empty screen ----------

function buildCards() {
  EXAMPLES.forEach(({ chapter, question }) => {
    const card = el("button", "card");
    card.type = "button";
    card.append(el("div", "card-chapter", chapter), el("div", "card-question", question));
    card.addEventListener("click", () => sendQuestion(question));
    cardsEl.append(card);
  });
}

// ---------- Sidebar ----------

// On phones the sidebar slides over the chat; on desktop it collapses in place.
function closeMobileSidebar() {
  sidebar.classList.remove("open");
  backdrop.classList.remove("show");
}

menuBtn.addEventListener("click", () => {
  if (MOBILE_QUERY.matches) {
    const open = sidebar.classList.toggle("open");
    backdrop.classList.toggle("show", open);
  } else {
    sidebar.classList.toggle("collapsed");
  }
});

backdrop.addEventListener("click", closeMobileSidebar);

newChatBtn.addEventListener("click", () => {
  activeChatId = null;
  renderChat();
  renderSidebar();
  closeMobileSidebar();
  input.focus();
});

// ---------- Init ----------

function init() {
  let savedTheme = null;
  try {
    savedTheme = localStorage.getItem(THEME_KEY);
  } catch {
    // Fall back to the default theme.
  }
  applyTheme(savedTheme || "dark");

  buildCards();
  renderSidebar();
  renderChat();
  autosize();
  input.focus();
}

init();
