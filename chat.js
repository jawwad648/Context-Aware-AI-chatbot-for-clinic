const $ = (s) => document.querySelector(s);
const messagesEl = $("#messages");
const debugEl = $("#debug");
const whoamiEl = $("#whoami");

function appendMessage(text, role) {
  const d = document.createElement("div");
  d.className = `msg ${role}`;
  d.textContent = text;
  messagesEl.appendChild(d);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(text) {
  appendMessage(text, "user");
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await r.json();
    appendMessage(data.reply, "bot");
    debugEl.textContent =
      `intent=${data.intent}  conf=${data.confidence}  ` +
      `flow=${data.state?.flow || "-"}  slots=${JSON.stringify(data.state?.slots || {})}`;
  } catch (e) {
    appendMessage("(network error)", "bot");
  }
}

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const inp = $("#msg");
  const v = inp.value.trim();
  if (!v) return;
  inp.value = "";
  sendMessage(v);
});

document.querySelectorAll("ul.examples li").forEach((li) => {
  li.addEventListener("click", () => sendMessage(li.textContent));
});

async function refreshWhoami() {
  const r = await fetch("/api/whoami");
  const d = await r.json();
  if (d.patient_id) {
    whoamiEl.textContent = `logged in as ${d.patient_name}`;
    whoamiEl.style.background = "#d1fae5";
    whoamiEl.style.color = "#065f46";
  } else {
    whoamiEl.textContent = "not logged in";
    whoamiEl.style.background = "";
    whoamiEl.style.color = "";
  }
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const r = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_no: fd.get("patient_no"),
      password: fd.get("password"),
    }),
  });
  const d = await r.json();
  if (d.ok) {
    appendMessage(`[system] logged in as ${d.patient_name}`, "bot");
    refreshWhoami();
  } else {
    appendMessage(`[system] login failed: ${d.error}`, "bot");
  }
});
$("#logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  appendMessage("[system] logged out.", "bot");
  refreshWhoami();
});

refreshWhoami();
appendMessage(
  "Hello! I'm the clinic's virtual receptionist. I can help with appointments, lab results, and general information. How can I help?",
  "bot"
);
