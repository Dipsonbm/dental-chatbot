(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Config — read from the script tag's query params
  // <script src="/widget.js?key=pub_xxxxx&color=2563eb"></script>
  // ---------------------------------------------------------------------------
  const scriptTag = document.currentScript;
  const params = new URLSearchParams(scriptTag.src.split("?")[1] || "");
  const WIDGET_KEY = params.get("key") || "";
  const ACCENT = "#" + (params.get("color") || "2563eb");
  const API_URL = scriptTag.src.split("/widget.js")[0] + "/api/chat";

  if (!WIDGET_KEY) {
    console.warn("[DentalBot] No widget key found in script tag. Widget disabled.");
    return;
  }

  // ---------------------------------------------------------------------------
  // Session ID — stable per browser tab session
  // ---------------------------------------------------------------------------
  let sessionId = sessionStorage.getItem("dentalbot_session");
  if (!sessionId) {
    sessionId = "sess_" + Math.random().toString(36).slice(2) + Date.now();
    sessionStorage.setItem("dentalbot_session", sessionId);
  }

  const localMessages = [];

  // ---------------------------------------------------------------------------
  // SVG icons
  // ---------------------------------------------------------------------------
  const TOOTH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
    <path d="M12 2C9.8 2 8.1 3.2 6.5 3.2C5 3.2 3.8 2.3 3.2 3.2C2.5 4.3 3.2 7.2 4.2 9.5C5 11.4 5.2 13.2 5.8 15.8C6.3 18 7 21.5 8.8 21.5C9.9 21.5 10.4 19.8 11.2 18.5C11.6 17.8 12 17.8 12 17.8C12 17.8 12.4 17.8 12.8 18.5C13.6 19.8 14.1 21.5 15.2 21.5C17 21.5 17.7 18 18.2 15.8C18.8 13.2 19 11.4 19.8 9.5C20.8 7.2 21.5 4.3 20.8 3.2C20.2 2.3 19 3.2 17.5 3.2C15.9 3.2 14.2 2 12 2Z"/>
  </svg>`;

  const CHAT_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
    <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H5.2L4 17.2V4H20V16Z"/>
  </svg>`;

  const CLOSE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
  </svg>`;

  const SEND_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>`;

  // ---------------------------------------------------------------------------
  // Styles
  // ---------------------------------------------------------------------------
  const style = document.createElement("style");
  style.textContent = `
    #dentalbot-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 58px; height: 58px; border-radius: 50%;
      background: ${ACCENT}; color: #fff; border: none;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 20px rgba(0,0,0,.28);
      transition: transform .15s, box-shadow .15s;
    }
    #dentalbot-btn:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(0,0,0,.32); }

    #dentalbot-panel {
      position: fixed; bottom: 96px; right: 24px; z-index: 99999;
      width: 370px; max-height: 560px;
      background: #fff; border-radius: 18px;
      box-shadow: 0 8px 40px rgba(0,0,0,.18);
      display: flex; flex-direction: column;
      font-family: system-ui, -apple-system, sans-serif; overflow: hidden;
      transition: opacity .2s, transform .2s;
    }
    #dentalbot-panel.hidden { opacity: 0; pointer-events: none; transform: translateY(14px); }

    #dentalbot-header {
      background: ${ACCENT};
      padding: 14px 16px;
      display: flex; align-items: center; gap: 12px;
    }
    #dentalbot-avatar {
      width: 42px; height: 42px; border-radius: 50%;
      background: rgba(255,255,255,0.2);
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; color: #fff;
    }
    #dentalbot-header-info { flex: 1; }
    #dentalbot-header-title { color: #fff; font-weight: 700; font-size: .95rem; line-height: 1.2; }
    #dentalbot-header-status {
      display: flex; align-items: center; gap: 5px;
      color: rgba(255,255,255,0.85); font-size: .78rem; margin-top: 2px;
    }
    #dentalbot-header-status::before {
      content: ''; width: 7px; height: 7px; border-radius: 50%;
      background: #4ade80; display: inline-block;
    }
    #dentalbot-close {
      background: rgba(255,255,255,0.15); border: none; color: #fff;
      width: 32px; height: 32px; border-radius: 50%;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background .15s;
    }
    #dentalbot-close:hover { background: rgba(255,255,255,0.25); }

    #dentalbot-messages {
      flex: 1; overflow-y: auto; padding: 16px 14px;
      display: flex; flex-direction: column; gap: 12px;
      background: #f8fafc;
    }
    #dentalbot-messages::-webkit-scrollbar { width: 4px; }
    #dentalbot-messages::-webkit-scrollbar-track { background: transparent; }
    #dentalbot-messages::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

    .db-row { display: flex; align-items: flex-end; gap: 8px; }
    .db-row.user { flex-direction: row-reverse; }

    .db-bot-icon {
      width: 28px; height: 28px; border-radius: 50%;
      background: ${ACCENT}; color: #fff;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; margin-bottom: 2px;
    }
    .db-bot-icon svg { width: 15px; height: 15px; }

    .db-msg {
      max-width: 78%; padding: 10px 14px; border-radius: 16px;
      font-size: .875rem; line-height: 1.5; word-break: break-word;
    }
    .db-msg.user {
      background: ${ACCENT}; color: #fff;
      border-bottom-right-radius: 4px;
    }
    .db-msg.bot {
      background: #fff; color: #1e293b;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }

    .db-typing {
      display: flex; align-items: center; gap: 4px;
      padding: 12px 16px;
    }
    .db-typing span {
      width: 7px; height: 7px; border-radius: 50%;
      background: #94a3b8; display: inline-block;
      animation: db-bounce .9s infinite ease-in-out;
    }
    .db-typing span:nth-child(2) { animation-delay: .15s; }
    .db-typing span:nth-child(3) { animation-delay: .3s; }
    @keyframes db-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-5px); }
    }

    #dentalbot-input-row {
      display: flex; gap: 8px; padding: 12px 14px;
      border-top: 1px solid #e2e8f0; background: #fff;
    }
    #dentalbot-input {
      flex: 1; padding: 10px 14px; border: 1.5px solid #e2e8f0;
      border-radius: 24px; font-size: .875rem; font-family: inherit;
      outline: none; background: #f8fafc; transition: border-color .15s;
    }
    #dentalbot-input:focus { border-color: ${ACCENT}; background: #fff; }
    #dentalbot-send {
      width: 40px; height: 40px; background: ${ACCENT}; color: #fff;
      border: none; border-radius: 50%; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background .15s, transform .1s;
    }
    #dentalbot-send:hover { transform: scale(1.06); }
    #dentalbot-send:disabled { opacity: .45; cursor: not-allowed; transform: none; }

    #dentalbot-footer {
      text-align: center; padding: 6px 0 8px;
      font-size: .7rem; color: #94a3b8; background: #fff;
      border-top: 1px solid #f1f5f9;
    }
    #dentalbot-footer a { color: #94a3b8; text-decoration: none; }
    #dentalbot-footer a:hover { color: #64748b; }

    @media (max-width: 420px) {
      #dentalbot-panel { width: calc(100vw - 32px); right: 16px; bottom: 84px; }
    }
  `;
  document.head.appendChild(style);

  // ---------------------------------------------------------------------------
  // DOM
  // ---------------------------------------------------------------------------
  const btn = document.createElement("button");
  btn.id = "dentalbot-btn";
  btn.setAttribute("aria-label", "Open chat");
  btn.innerHTML = CHAT_SVG;

  const panel = document.createElement("div");
  panel.id = "dentalbot-panel";
  panel.classList.add("hidden");
  panel.innerHTML = `
    <div id="dentalbot-header">
      <div id="dentalbot-avatar">${TOOTH_SVG}</div>
      <div id="dentalbot-header-info">
        <div id="dentalbot-header-title">AI Dental Assistant</div>
        <div id="dentalbot-header-status">Online</div>
      </div>
      <button id="dentalbot-close" aria-label="Close chat">${CLOSE_SVG}</button>
    </div>
    <div id="dentalbot-messages"></div>
    <div id="dentalbot-input-row">
      <input id="dentalbot-input" type="text" placeholder="Type a message…" autocomplete="off" />
      <button id="dentalbot-send" aria-label="Send">${SEND_SVG}</button>
    </div>
    <div id="dentalbot-footer">Powered by <a href="#" tabindex="-1">DentalBot AI</a></div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#dentalbot-messages");
  const inputEl    = panel.querySelector("#dentalbot-input");
  const sendEl     = panel.querySelector("#dentalbot-send");

  // ---------------------------------------------------------------------------
  // Toggle panel
  // ---------------------------------------------------------------------------
  let opened = false;

  btn.addEventListener("click", () => {
    opened = !opened;
    panel.classList.toggle("hidden", !opened);
    btn.innerHTML = opened ? CLOSE_SVG : CHAT_SVG;
    if (opened && localMessages.length === 0) {
      appendBotMessage("Hi! How can I help you today?");
    }
    if (opened) inputEl.focus();
  });

  panel.querySelector("#dentalbot-close").addEventListener("click", () => {
    opened = false;
    panel.classList.add("hidden");
    btn.innerHTML = CHAT_SVG;
  });

  // ---------------------------------------------------------------------------
  // Messaging
  // ---------------------------------------------------------------------------
  function appendMessage(text, role) {
    const row = document.createElement("div");
    row.className = "db-row " + role;

    if (role === "bot") {
      const icon = document.createElement("div");
      icon.className = "db-bot-icon";
      icon.innerHTML = TOOTH_SVG;
      row.appendChild(icon);
    }

    const bubble = document.createElement("div");
    bubble.className = "db-msg " + role;
    bubble.textContent = text;
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    localMessages.push({ role, text });
    return row;
  }

  function appendBotMessage(text) { return appendMessage(text, "bot"); }
  function appendUserMessage(text) { return appendMessage(text, "user"); }

  function showTyping() {
    const row = document.createElement("div");
    row.className = "db-row bot";

    const icon = document.createElement("div");
    icon.className = "db-bot-icon";
    icon.innerHTML = TOOTH_SVG;
    row.appendChild(icon);

    const bubble = document.createElement("div");
    bubble.className = "db-msg bot db-typing";
    bubble.innerHTML = "<span></span><span></span><span></span>";
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return row;
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = "";
    sendEl.disabled = true;
    appendUserMessage(text);

    const typingRow = showTyping();

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          widget_key: WIDGET_KEY,
          message: text,
          session_id: sessionId,
        }),
      });

      if (!res.ok) throw new Error("Server error " + res.status);

      const data = await res.json();
      typingRow.remove();
      appendBotMessage(data.reply);
    } catch (err) {
      typingRow.remove();
      appendBotMessage("Sorry, something went wrong. Please try again or call us directly.");
      console.error("[DentalBot]", err);
    } finally {
      sendEl.disabled = false;
      inputEl.focus();
    }
  }

  sendEl.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();
