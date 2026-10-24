
const API_BASE_URL = (
  window.MYDATA_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const $ = (id) => document.getElementById(id);
const state = {
  records: [],
  conversations: [],
  conversationId: null,
  busy: false,
};

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[ch]);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showNotice(id, message, type = "") {
  const node = $(id);
  node.textContent = message;
  node.className = `notice ${type}`;
}

function setServerStatus(online, text) {
  $("serverStatus").textContent = text;
  document.querySelector(".dot").classList.toggle("online", online);
}

function fmt(value) {
  return Number(value || 0).toLocaleString("ko-KR", { maximumFractionDigits: 1 });
}

function appendMessage(role, content) {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  row.appendChild(bubble);
  $("chatMessages").appendChild(row);
  $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
}

function renderMessages(messages) {
  $("chatMessages").replaceChildren();
  if (!messages?.length) {
    appendMessage("assistant", "새 대화입니다. 운동 기록에 대해 무엇이든 물어보세요.");
    return;
  }
  for (const msg of messages) {
    if (["user", "assistant"].includes(msg.role)) {
      appendMessage(msg.role, msg.content);
    }
  }
}

async function loadSummary() {
  const summary = await api("/api/data/summary");
  const metrics = summary.metrics || {};
  $("totalMinutes").textContent = fmt(metrics.total_minutes);
  $("totalCalories").textContent = fmt(metrics.total_calories);
  $("activeDays").textContent = fmt(metrics.active_days);
  $("trend").textContent = summary.trend || "—";
  $("period").textContent = summary.period || "데이터 없음";
  $("recordCount").textContent = `${fmt(summary.count)}건`;
  $("averageMinutes").textContent = `${fmt(metrics.average_minutes)}분`;
  $("maxMinutes").textContent = `${fmt(metrics.max_minutes)}분`;
  $("minMinutes").textContent = `${fmt(metrics.min_minutes)}분`;

  const comparison = summary.weekly_comparison;
  if (!comparison || comparison.change_percent === null) {
    $("weeklyChange").textContent = "비교 데이터 부족";
  } else {
    const sign = comparison.change_percent > 0 ? "+" : "";
    $("weeklyChange").textContent = `${sign}${comparison.change_percent}%`;
  }
}

async function loadRecords() {
  const result = await api("/api/data?limit=2000");
  state.records = result.items || [];
  renderRecords();
}

function renderRecords() {
  const tbody = $("exerciseRows");
  tbody.replaceChildren();

  const rows = [...state.records].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 30);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5">기록이 없습니다. 첫 운동을 추가해 보세요.</td></tr>';
    return;
  }

  for (const record of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHTML(record.date)}</td>
      <td>${escapeHTML(record.exercise_type)}</td>
      <td>${fmt(record.value)}분</td>
      <td>${fmt(record.calories)} kcal</td>
      <td><div class="row-actions">
        <button class="text-button" data-edit="${escapeHTML(record.id)}">수정</button>
        <button class="text-button danger" data-delete="${escapeHTML(record.id)}">삭제</button>
      </div></td>`;
    tbody.appendChild(tr);
  }
}

function resetExerciseForm() {
  $("exerciseForm").reset();
  $("recordId").value = "";
  $("exerciseDate").value = new Date().toLocaleDateString("sv-SE");
  $("exerciseCalories").value = "0";
  $("saveExerciseBtn").textContent = "기록 추가";
  $("cancelEditBtn").classList.add("hidden");
}

async function refreshAll() {
  try {
    setServerStatus(false, "데이터 불러오는 중");
    await Promise.all([loadSummary(), loadRecords(), loadConversations()]);
    setServerStatus(true, "서버 연결됨");
  } catch (error) {
    setServerStatus(false, "서버 연결 확인 필요");
    showNotice("dataNotice", error.message, "error");
  }
}

$("exerciseForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("recordId").value;
  const payload = {
    date: $("exerciseDate").value,
    exercise_type: $("exerciseType").value,
    value: Number($("exerciseValue").value),
    calories: Number($("exerciseCalories").value),
    memo: $("exerciseMemo").value.trim(),
  };

  $("saveExerciseBtn").disabled = true;
  try {
    await api(id ? `/api/data/${encodeURIComponent(id)}` : "/api/data", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showNotice("dataNotice", id ? "운동 기록을 수정했습니다." : "운동 기록을 저장했습니다.", "success");
    resetExerciseForm();
    await Promise.all([loadRecords(), loadSummary()]);
  } catch (error) {
    showNotice("dataNotice", error.message, "error");
  } finally {
    $("saveExerciseBtn").disabled = false;
  }
});

$("exerciseRows").addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");

  if (editButton) {
    const record = state.records.find((item) => item.id === editButton.dataset.edit);
    if (!record) return;
    $("recordId").value = record.id;
    $("exerciseDate").value = record.date;
    $("exerciseType").value = record.exercise_type || "기타";
    $("exerciseValue").value = record.value;
    $("exerciseCalories").value = record.calories ?? 0;
    $("exerciseMemo").value = record.memo || "";
    $("saveExerciseBtn").textContent = "수정 저장";
    $("cancelEditBtn").classList.remove("hidden");
    $("exerciseForm").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  if (deleteButton && confirm("이 운동 기록을 삭제할까요?")) {
    try {
      await api(`/api/data/${encodeURIComponent(deleteButton.dataset.delete)}`, { method: "DELETE" });
      showNotice("dataNotice", "운동 기록을 삭제했습니다.", "success");
      await Promise.all([loadRecords(), loadSummary()]);
    } catch (error) {
      showNotice("dataNotice", error.message, "error");
    }
  }
});

$("cancelEditBtn").addEventListener("click", resetExerciseForm);
$("refreshBtn").addEventListener("click", refreshAll);
$("loadDataBtn").addEventListener("click", refreshAll);

async function loadConversations() {
  const result = await api("/api/conversations");
  state.conversations = result.items || [];
  renderConversations();
}

function renderConversations() {
  const list = $("conversationList");
  list.replaceChildren();

  if (!state.conversations.length) {
    list.innerHTML = '<p class="subtle">아직 저장된 대화가 없습니다.</p>';
    return;
  }

  for (const item of state.conversations) {
    const row = document.createElement("div");
    row.className = "conversation-item";

    const open = document.createElement("button");
    open.className = "conversation-open";
    open.type = "button";
    const title = document.createElement("strong");
    title.textContent = item.title || "새 대화";
    const date = document.createElement("small");
    date.textContent = `${item.message_count || 0}개 메시지 · ${String(item.updated_at || "").slice(0, 10)}`;
    open.append(title, date);
    open.addEventListener("click", () => openConversation(item.id));

    const del = document.createElement("button");
    del.className = "delete-conversation";
    del.type = "button";
    del.textContent = "×";
    del.title = "대화 삭제";
    del.addEventListener("click", async () => {
      if (!confirm("이 대화를 삭제할까요?")) return;
      try {
        await api(`/api/conversations/${encodeURIComponent(item.id)}`, { method: "DELETE" });
        if (state.conversationId === item.id) {
          state.conversationId = null;
          renderMessages([]);
        }
        await loadConversations();
      } catch (error) {
        showNotice("chatNotice", error.message, "error");
      }
    });

    row.append(open, del);
    list.appendChild(row);
  }
}

async function openConversation(id) {
  try {
    const conversation = await api(`/api/conversations/${encodeURIComponent(id)}`);
    state.conversationId = conversation.id;
    renderMessages(conversation.messages || []);
    showNotice("chatNotice", `대화를 불러왔습니다: ${conversation.title || "새 대화"}`, "success");
  } catch (error) {
    showNotice("chatNotice", error.message, "error");
  }
}

$("newChatBtn").addEventListener("click", () => {
  state.conversationId = null;
  renderMessages([]);
  showNotice("chatNotice", "새 대화를 시작합니다.");
  $("chatInput").focus();
});

async function sendChat(message) {
  if (state.busy) return;
  state.busy = true;
  $("sendBtn").disabled = true;
  $("chatInput").disabled = true;

  appendMessage("user", message);
  const loading = document.createElement("div");
  loading.className = "message assistant";
  loading.id = "loadingMessage";
  loading.innerHTML = '<div class="bubble">운동 기록을 분석하고 있습니다…</div>';
  $("chatMessages").appendChild(loading);
  $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
  showNotice("chatNotice", "서버 응답을 기다리는 중입니다. 첫 요청은 시간이 걸릴 수 있습니다.");

  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: state.conversationId,
        message,
      }),
    });
    state.conversationId = result.conversation_id;
    loading.remove();
    appendMessage("assistant", result.answer);
    await loadConversations();
    showNotice("chatNotice", "답변과 대화 기록이 저장되었습니다.", "success");
  } catch (error) {
    loading.remove();
    appendMessage("assistant", `요청에 실패했습니다: ${error.message}`);
    showNotice("chatNotice", error.message, "error");
  } finally {
    state.busy = false;
    $("sendBtn").disabled = false;
    $("chatInput").disabled = false;
    $("chatInput").focus();
  }
}

$("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = $("chatInput").value.trim();
  if (!message) return;
  $("chatInput").value = "";
  await sendChat(message);
});

$("chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("chatForm").requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    $("chatInput").value = button.textContent.trim();
    $("chatInput").focus();
  });
});

resetExerciseForm();
refreshAll();
