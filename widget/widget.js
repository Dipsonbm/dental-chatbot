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

  // Local message log — for rendering the UI only, NOT sent to backend
  const localMessages = [];

  // ---------------------------------------------------------------------------
  // Styles
  // ---------------------------------------------------------------------------
  const style = document.createElement("style");
  style.textContent = `
    #dentalbot-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 56px; height: 56px; border-radius: 50%;
      background: ${ACCENT}; color: #fff; border: none;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 16px rgba(0,0,0,.22);
      font-size: 26px; transition: transform .15s;
    }
    #dentalbot-btn:hover { transform: scale(1.08); }

    #dentalbot-panel {
      position: fixed; bottom: 92px; right: 24px; z-index: 99999;
      width: 360px; max-height: 520px;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,.18);
      display: flex; flex-direction: column;
      font-family: system-ui, sans-serif; overflow: hidden;
      transition: opacity .2s, transform .2s;
    }
    #dentalbot-panel.hidden { opacity: 0; pointer-events: none; transform: translateY(12px); }

    #dentalbot-header {
      background: ${ACCENT}; color: #fff;
      padding: 16px 18px; font-weight: 700; font-size: .95rem;
      display: flex; align-items: center; justify-content: space-between;
    }
    #dentalbot-header span { opacity: .85; font-size: .8rem; font-weight: 400; margin-top: 2px; }
    #dentalbot-close { background: none; border: none; color: #fff;
                       font-size: 20px; cursor: pointer; line-height: 1; }

    #dentalbot-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 10px;
    }

    .db-msg { max-width: 82%; padding: 10px 14px; border-radius: 12px;
              font-size: .88rem; line-height: 1.45; word-break: break-word; }
    .db-msg.user { background: ${ACCENT}; color: #fff; align-self: flex-end;
                   border-bottom-right-radius: 4px; }
    .db-msg.bot  { background: #f1f5f9; color: #1a1a2e; align-self: flex-start;
                   border-bottom-left-radius: 4px; }
    .db-msg.typing { opacity: .6; font-style: italic; }

    #dentalbot-input-row {
      display: flex; gap: 8px; padding: 12px 14px;
      border-top: 1px solid #e2e8f0;
    }
    #dentalbot-input {
      flex: 1; padding: 9px 12px; border: 1px solid #d0d5dd;
      border-radius: 8px; font-size: .88rem; font-family: inherit; outline: none;
    }
    #dentalbot-input:focus { border-color: ${ACCENT}; }
    #dentalbot-send {
      padding: 9px 14px; background: ${ACCENT}; color: #fff;
      border: none; border-radius: 8px; cursor: pointer; font-size: .88rem;
      font-weight: 600;
    }
    #dentalbot-send:disabled { opacity: .5; cursor: not-allowed; }

    @media (max-width: 420px) {
      #dentalbot-panel { width: calc(100vw - 32px); right: 16px; bottom: 80px; }
    }
  `;
  document.head.appendChild(style);

  // ---------------------------------------------------------------------------
  // DOM
  // ---------------------------------------------------------------------------
  const btn = document.createElement("button");
  btn.id = "dentalbot-btn";
  btn.setAttribute("aria-label", "Open chat");
  btn.textContent = "💬";

  const panel = document.createElement("div");
  panel.id = "dentalbot-panel";
  panel.classList.add("hidden");
  panel.innerHTML = `
    <div id="dentalbot-header">
      <div>
        <div>Chat with us</div>
        <span>We typically reply instantly</span>
      </div>
      <button id="dentalbot-close" aria-label="Close chat">✕</button>
    </div>
    <div id="dentalbot-messages"></div>
    <div id="dentalbot-input-row">
      <input id="dentalbot-input" type="text" placeholder="Type a message…" autocomplete="off" />
      <button id="dentalbot-send">Send</button>
    </div>
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
    btn.textContent = opened ? "✕" : "💬";
    if (opened && localMessages.length === 0) {
      appendBotMessage("Hi! How can I help you today?");
    }
    if (opened) inputEl.focus();
  });

  panel.querySelector("#dentalbot-close").addEventListener("click", () => {
    opened = false;
    panel.classList.add("hidden");
    btn.textContent = "💬";
  });

  // ---------------------------------------------------------------------------
  // Messaging
  // ---------------------------------------------------------------------------
  function appendMessage(text, role) {
    const el = document.createElement("div");
    el.className = "db-msg " + role;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    localMessages.push({ role, text });
    return el;
  }

  function appendBotMessage(text) { return appendMessage(text, "bot"); }
  function appendUserMessage(text) { return appendMessage(text, "user"); }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "db-msg bot typing";
    el.textContent = "…";
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = "";
    sendEl.disabled = true;
    appendUserMessage(text);

    const typingEl = showTyping();

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

      if (!res.ok) {
        throw new Error("Server error " + res.status);
      }

      const data = await res.json();
      typingEl.remove();
      appendBotMessage(data.reply);
    } catch (err) {
      typingEl.remove();
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
