const socket = io();

const state = {
  joined: false,
  mode: "create",
  room: "",
  username: "",
};

const elements = {
  createModeBtn: document.querySelector("#createModeBtn"),
  joinModeBtn: document.querySelector("#joinModeBtn"),
  joinPanel: document.querySelector("#joinPanel"),
  username: document.querySelector("#username"),
  roomCodeLabel: document.querySelector("#roomCodeLabel"),
  roomId: document.querySelector("#roomId"),
  newRoomBtn: document.querySelector("#newRoomBtn"),
  joinBtn: document.querySelector("#joinBtn"),
  copyLinkBtn: document.querySelector("#copyLinkBtn"),
  roomTitle: document.querySelector("#roomTitle"),
  userCount: document.querySelector("#userCount"),
  userList: document.querySelector("#userList"),
  connectionText: document.querySelector("#connectionText"),
  chatTitle: document.querySelector("#chatTitle"),
  leaveBtn: document.querySelector("#leaveBtn"),
  messages: document.querySelector("#messages"),
  emptyState: document.querySelector("#emptyState"),
  messageForm: document.querySelector("#messageForm"),
  messageInput: document.querySelector("#messageInput"),
  fileInput: document.querySelector("#fileInput"),
  sendBtn: document.querySelector("#sendBtn"),
};

function createRoomCode() {
  const randomPart = crypto.getRandomValues(new Uint32Array(2));
  return [...randomPart].map((value) => value.toString(36)).join("-").slice(0, 15);
}

function extractRoomCode(value) {
  const trimmed = value.trim();
  if (!trimmed) return "";

  try {
    const url = new URL(trimmed);
    return url.searchParams.get("room") || trimmed;
  } catch {
    return trimmed;
  }
}

function getRoomFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("room") || "";
}

function setUrlRoom(room) {
  const url = new URL(window.location.href);
  url.searchParams.set("room", room);
  history.replaceState({}, "", url);
}

function setJoinedUi(isJoined) {
  elements.messageInput.disabled = !isJoined;
  elements.sendBtn.disabled = !isJoined;
  elements.leaveBtn.disabled = !isJoined;
  elements.copyLinkBtn.disabled = !isJoined;
  elements.joinBtn.disabled = isJoined;
  elements.newRoomBtn.disabled = isJoined;
  elements.roomId.disabled = isJoined;
  elements.username.disabled = isJoined;
  elements.createModeBtn.disabled = isJoined;
  elements.joinModeBtn.disabled = isJoined;
}

function setMode(mode) {
  state.mode = mode;
  const isCreate = mode === "create";

  elements.createModeBtn.classList.toggle("active", isCreate);
  elements.joinModeBtn.classList.toggle("active", !isCreate);
  elements.joinPanel.classList.toggle("join-active", !isCreate);
  elements.roomCodeLabel.textContent = isCreate ? "New room code" : "Room code or share link";
  elements.roomId.placeholder = isCreate ? "Auto-generated room code" : "Paste room code or share link";
  elements.newRoomBtn.style.display = isCreate ? "grid" : "none";
  elements.joinBtn.textContent = isCreate ? "Create Room" : "Join Room";
  elements.chatTitle.textContent = isCreate ? "Create a room and share the link" : "Join a room with a code or link";

  if (isCreate && !elements.roomId.value.trim()) {
    elements.roomId.value = createRoomCode();
  }
  if (!isCreate) {
    elements.roomId.value = getRoomFromUrl() || "";
  }
}

function escapeText(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

function addSystemMessage(message) {
  hideEmptyState();
  const row = document.createElement("div");
  row.className = "system-message";
  row.textContent = message;
  elements.messages.appendChild(row);
  scrollMessages();
}

function addChatMessage({ username, message, time }) {
  hideEmptyState();
  const row = document.createElement("article");
  row.className = `message ${username === state.username ? "own" : ""}`;
  row.innerHTML = `
    <div class="message-meta">
      <span>${escapeText(username)}</span>
      <span>${escapeText(time || "")}</span>
    </div>
    <div class="message-body">${escapeText(message)}</div>
  `;
  elements.messages.appendChild(row);
  scrollMessages();
}

function addAttachment({ username, filename, filetype, content, time }) {
  hideEmptyState();
  const row = document.createElement("article");
  row.className = `message ${username === state.username ? "own" : ""}`;
  const safeName = escapeText(filename);
  const isImage = filetype.startsWith("image/");
  row.innerHTML = `
    <div class="message-meta">
      <span>${escapeText(username)}</span>
      <span>${escapeText(time || "")}</span>
    </div>
    <div class="message-body">
      <a class="attachment-link" href="${content}" download="${safeName}">${safeName}</a>
      ${isImage ? `<img class="attachment-preview" src="${content}" alt="${safeName}" />` : ""}
    </div>
  `;
  elements.messages.appendChild(row);
  scrollMessages();
}

function hideEmptyState() {
  if (elements.emptyState) {
    elements.emptyState.remove();
    elements.emptyState = null;
  }
}

function scrollMessages() {
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function renderUsers(users = []) {
  elements.userList.innerHTML = "";
  elements.userCount.textContent = users.length;

  users.forEach((user) => {
    const item = document.createElement("li");
    item.textContent = user;
    elements.userList.appendChild(item);
  });
}

function joinRoom() {
  const username = elements.username.value.trim();
  const roomInput = extractRoomCode(elements.roomId.value);
  const room = state.mode === "create" ? roomInput || createRoomCode() : roomInput;

  if (!username) {
    addSystemMessage("Enter a display name first.");
    elements.username.focus();
    return;
  }

  if (!room) {
    addSystemMessage("Paste a room code or share link first.");
    elements.roomId.focus();
    return;
  }

  state.username = username;
  state.room = room;
  elements.joinBtn.textContent = state.mode === "create" ? "Creating..." : "Joining...";
  elements.joinBtn.disabled = true;
  socket.emit("join", { username, room });
}

function leaveRoom() {
  if (!state.joined) return;

  socket.emit("leave", { room: state.room });
  state.joined = false;
  state.room = "";
  state.username = "";
  elements.connectionText.textContent = "Disconnected";
  elements.chatTitle.textContent = state.mode === "create" ? "Create a room and share the link" : "Join a room with a code or link";
  elements.roomTitle.textContent = "Not connected";
  renderUsers([]);
  setJoinedUi(false);
  elements.joinBtn.textContent = state.mode === "create" ? "Create Room" : "Join Room";
  addSystemMessage("You left the room.");
}

function sendMessage(event) {
  event.preventDefault();
  const message = elements.messageInput.value.trim();
  if (!state.joined || !message) return;

  socket.emit("chat_message", { room: state.room, message });
  elements.messageInput.value = "";
}

function sendAttachment() {
  const file = elements.fileInput.files[0];
  if (!state.joined || !file) return;

  const maxSize = 6 * 1024 * 1024;
  if (file.size > maxSize) {
    addSystemMessage("Choose a file smaller than 6 MB.");
    elements.fileInput.value = "";
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    socket.emit("attachment", {
      room: state.room,
      filename: file.name,
      filetype: file.type || "application/octet-stream",
      content: reader.result,
    });
    elements.fileInput.value = "";
  };
  reader.readAsDataURL(file);
}

async function copyShareLink() {
  if (!state.joined) return;

  const url = new URL(window.location.href);
  url.searchParams.set("room", state.room);
  await navigator.clipboard.writeText(url.toString());
  addSystemMessage("Share link copied.");
}

elements.newRoomBtn.addEventListener("click", () => {
  elements.roomId.value = createRoomCode();
  elements.roomId.classList.add("pulse");
  window.setTimeout(() => elements.roomId.classList.remove("pulse"), 450);
});
elements.createModeBtn.addEventListener("click", () => setMode("create"));
elements.joinModeBtn.addEventListener("click", () => setMode("join"));
elements.joinBtn.addEventListener("click", joinRoom);
elements.leaveBtn.addEventListener("click", leaveRoom);
elements.copyLinkBtn.addEventListener("click", copyShareLink);
elements.messageForm.addEventListener("submit", sendMessage);
elements.fileInput.addEventListener("change", sendAttachment);

socket.on("joined", ({ room, username, users }) => {
  state.joined = true;
  state.room = room;
  state.username = username;
  elements.roomId.value = room;
  elements.username.value = username;
  elements.connectionText.textContent = "Connected";
  elements.chatTitle.textContent = state.mode === "create" ? `Room created: ${room}` : `Joined room: ${room}`;
  elements.roomTitle.textContent = room;
  setUrlRoom(room);
  renderUsers(users);
  setJoinedUi(true);
  elements.joinBtn.textContent = state.mode === "create" ? "Create Room" : "Join Room";
  addSystemMessage(state.mode === "create" ? `Room ${room} created.` : `Joined room ${room}.`);
  elements.messageInput.focus();
});

socket.on("chat_message", addChatMessage);
socket.on("attachment", addAttachment);

socket.on("system_message", ({ message, users }) => {
  addSystemMessage(message);
  renderUsers(users);
});

socket.on("error_message", ({ message }) => {
  elements.joinBtn.disabled = false;
  elements.joinBtn.textContent = state.mode === "create" ? "Create Room" : "Join Room";
  addSystemMessage(message);
});

socket.on("connect_error", () => {
  elements.joinBtn.disabled = false;
  elements.joinBtn.textContent = state.mode === "create" ? "Create Room" : "Join Room";
  addSystemMessage("Could not connect to the chat server.");
});

socket.on("disconnect", () => {
  if (!state.joined) return;
  state.joined = false;
  setJoinedUi(false);
  elements.connectionText.textContent = "Disconnected";
  elements.joinBtn.textContent = state.mode === "create" ? "Create Room" : "Join Room";
  addSystemMessage("Connection lost. Refresh the page to reconnect.");
});

const initialRoom = getRoomFromUrl();
if (initialRoom) {
  elements.roomId.value = initialRoom;
  setMode("join");
}
if (!elements.roomId.value) {
  elements.roomId.value = createRoomCode();
}
if (!initialRoom) {
  setMode("create");
}
setJoinedUi(false);
