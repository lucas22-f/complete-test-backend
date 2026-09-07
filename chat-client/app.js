// This client reads POST SSE frames and accumulates message_delta events.
const $ = (selector) => document.querySelector(selector);
const form = $("#chat-form");
const messages = $("#messages");
const sendButton = $("#send-button");
const status = $("#connection-status");

function setStatus(text, kind = "") {
  status.textContent = text;
  status.className = `status-pill ${kind}`;
}

function addMessage(text, kind, meta = "") {
  const element = document.createElement("div");
  element.className = `message ${kind}`;
  element.textContent = text;
  if (meta) {
    const details = document.createElement("small");
    details.className = "meta";
    details.textContent = meta;
    element.append(details);
  }
  messages.querySelector(".empty-state")?.remove();
  messages.append(element);
  messages.scrollTop = messages.scrollHeight;
  return element;
}

async function consumeSse(response, agentMessage) {
  if (!response.body) throw new Error("The browser did not expose a response stream.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload;

  const processFrame = (frame) => {
    const eventName = frame.match(/^event: (.+)$/m)?.[1];
    const dataLine = frame.match(/^data: (.+)$/m)?.[1];
    if (!eventName || !dataLine) return;
    const data = JSON.parse(dataLine);
    if (eventName === "message_delta") {
      agentMessage.textContent += data.delta;
      messages.scrollTop = messages.scrollHeight;
    } else if (eventName === "completed") {
      finalPayload = data;
    } else if (eventName === "error") {
      throw new Error(data.code || "Agent generation failed");
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    frames.forEach(processFrame);
    if (done) break;
  }
  if (buffer.trim()) processFrame(buffer);
  if (!finalPayload) throw new Error("The stream ended without a completed event.");
  return finalPayload;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const messageInput = $("#message");
  const message = messageInput.value.trim();
  const token = $("#token").value.trim();
  if (!message || !token) return addMessage("Enter a message and a JWT first.", "error");

  addMessage(message, "user");
  const agentMessage = addMessage("", "agent");
  messageInput.value = "";
  sendButton.disabled = true;
  setStatus("Streaming…", "busy");

  try {
    const response = await fetch($("#api-url").value.trim(), {
      method: "POST",
      headers: { Accept: "text/event-stream", "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ thread_id: $("#thread-id").value.trim(), message }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const completed = await consumeSse(response, agentMessage);
    const actionCount = completed.actions?.length || 0;
    const sourceCount = completed.sources?.length || 0;
    agentMessage.insertAdjacentHTML("beforeend", `<small class="meta">${actionCount} action(s) · ${sourceCount} source(s)</small>`);
    setStatus("Connected", "");
  } catch (error) {
    agentMessage.remove();
    addMessage(error.message, "error");
    setStatus("Error", "error");
  } finally {
    sendButton.disabled = false;
    messageInput.focus();
  }
});
