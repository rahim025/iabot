const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const messagesEl = document.getElementById("messages");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const modelSelect = document.getElementById("model-select");
const conversationList = document.getElementById("conversation-list");
const exportPdfBtn = document.getElementById("export-pdf-btn");

let currentConversationId = null;

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function clearMessages() {
  messagesEl.innerHTML = "";
}

async function loadConversation(convId) {
  currentConversationId = convId;
  clearMessages();
  document.querySelectorAll(".conv-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id == convId);
  });
  const res = await fetch(`/api/conversations/${convId}/messages`);
  if (!res.ok) return;
  const msgs = await res.json();
  msgs.forEach((m) => addMessage(m.content, m.role === "assistant" ? "bot" : "user"));
  renderMath();
}

async function createConversation() {
  const res = await fetch("/api/conversations/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelSelect.value }),
  });
  const conv = await res.json();
  const item = document.createElement("div");
  item.className = "conv-item active";
  item.dataset.id = conv.id;
  item.innerHTML = `<span class="conv-title">${conv.title}</span><button class="conv-delete" data-id="${conv.id}" title="Supprimer">✕</button>`;
  document.querySelectorAll(".conv-item").forEach((el) => el.classList.remove("active"));
  conversationList.prepend(item);
  currentConversationId = conv.id;
  clearMessages();
}

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
});

newChatBtn.addEventListener("click", createConversation);

exportPdfBtn.addEventListener("click", () => {
  if (!currentConversationId) {
    alert("Ouvre ou démarre une conversation avant d'exporter.");
    return;
  }
  window.location.href = `/api/conversations/${currentConversationId}/export-pdf`;
});

function renderMath() {
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise([messagesEl]).catch(() => {});
  }
}

conversationList.addEventListener("click", async (e) => {
  if (e.target.classList.contains("conv-delete")) {
    e.stopPropagation();
    const id = e.target.dataset.id;
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    e.target.closest(".conv-item").remove();
    if (currentConversationId == id) {
      currentConversationId = null;
      clearMessages();
    }
    return;
  }
  const item = e.target.closest(".conv-item");
  if (item) loadConversation(item.dataset.id);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  if (!currentConversationId) {
    await createConversation();
  }

  addMessage(message, "user");
  input.value = "";
  input.style.height = "auto";
  sendBtn.disabled = true;

  const botDiv = addMessage("", "bot");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: currentConversationId }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") continue;
        const data = JSON.parse(payload);
        if (data.chunk) {
          botDiv.textContent += data.chunk;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (data.error) {
          botDiv.className = "msg error";
          botDiv.textContent = "Erreur : " + data.error;
        }
      }
    }
  } catch (err) {
    botDiv.className = "msg error";
    botDiv.textContent = "Erreur de connexion.";
  } finally {
    sendBtn.disabled = false;
    renderMath();
  }
});
