const state = {
  apiBase: localStorage.getItem("teamtool_api_base") || "http://127.0.0.1:8000/api",
  token: localStorage.getItem("teamtool_token") || "",
  me: null,
  users: [],
  chats: [],
  currentChatId: null,
  messages: [],
  tasks: [],
  worklogs: [],
  notes: [],
  currentView: "dashboard",
};

const el = {
  authView: document.getElementById("authView"),
  appView: document.getElementById("appView"),
  loginForm: document.getElementById("loginForm"),
  registerForm: document.getElementById("registerForm"),
  logoutBtn: document.getElementById("logoutBtn"),
  currentUser: document.getElementById("currentUser"),
  apiBaseInput: document.getElementById("apiBaseInput"),
  alerts: document.getElementById("alerts"),
  navTabs: document.getElementById("navTabs"),
  viewTitle: document.getElementById("viewTitle"),
  views: {
    dashboard: document.getElementById("dashboard"),
    chats: document.getElementById("chats"),
    tasks: document.getElementById("tasks"),
    weekplan: document.getElementById("weekplan"),
    notes: document.getElementById("notes"),
    users: document.getElementById("users"),
  },
};

el.apiBaseInput.value = state.apiBase;

function alertMsg(text, type = "ok") {
  const node = document.createElement("div");
  node.className = `alert ${type === "err" ? "err" : "ok"}`;
  node.textContent = text;
  el.alerts.prepend(node);
  setTimeout(() => node.remove(), 3500);
}

function setAuth(token) {
  state.token = token;
  if (token) {
    localStorage.setItem("teamtool_token", token);
  } else {
    localStorage.removeItem("teamtool_token");
  }
}

function setApiBase(base) {
  state.apiBase = base.replace(/\/$/, "");
  localStorage.setItem("teamtool_api_base", state.apiBase);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!headers["Content-Type"] && options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) headers.Authorization = `Bearer ${state.token}`;

  const res = await fetch(`${state.apiBase}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API Fehler (${res.status})`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return null;
}

function renderView() {
  Object.entries(el.views).forEach(([key, node]) => {
    node.classList.toggle("hidden", key !== state.currentView);
  });

  [...el.navTabs.querySelectorAll(".nav-item")].forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === state.currentView);
  });

  const labelMap = {
    dashboard: "Dashboard",
    chats: "Chats",
    tasks: "Task Ablauf",
    weekplan: "Wochenplan",
    notes: "Notizen",
    users: "User",
  };
  el.viewTitle.textContent = labelMap[state.currentView] || "TeamTool";
}

function startOfWeek(d = new Date()) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  return date.toISOString().slice(0, 10);
}

function toFormData(fields) {
  const form = new URLSearchParams();
  for (const [k, v] of Object.entries(fields)) form.set(k, String(v));
  return form;
}

async function loadMe() {
  state.me = await api("/auth/me");
  el.currentUser.textContent = `${state.me.full_name} (${state.me.email})`;
}

async function loadUsers() {
  state.users = await api("/users");
}

async function loadChats() {
  state.chats = await api("/chats");
  if (!state.currentChatId && state.chats[0]) state.currentChatId = state.chats[0].id;
}

async function loadMessages() {
  if (!state.currentChatId) {
    state.messages = [];
    return;
  }
  state.messages = await api(`/chats/${state.currentChatId}/messages`);
}

async function loadTasks() {
  state.tasks = await api("/tasks");
}

async function loadWeeklogs(weekStart = startOfWeek()) {
  state.worklogs = await api(`/worklogs/week?week_start=${weekStart}`);
}

async function loadNotes() {
  state.notes = await api("/notes");
}

function dashboardHtml() {
  const done = state.tasks.filter((t) => t.status === "done").length;
  const progress = state.tasks.filter((t) => t.status === "in_progress").length;
  const planned = state.tasks.filter((t) => t.status === "planned").length;
  const weekHours = state.worklogs.reduce((sum, w) => sum + Number(w.hours || 0), 0).toFixed(2);

  return `
    <div class="grid-3">
      <article class="panel card kpi"><p class="eyebrow">Tasks</p><h3>${state.tasks.length}</h3><p class="muted">Alle sichtbaren Auftraege</p></article>
      <article class="panel card kpi"><p class="eyebrow">Aktive Woche</p><h3>${weekHours}h</h3><p class="muted">Erfasste Stunden</p></article>
      <article class="panel card kpi"><p class="eyebrow">Chats</p><h3>${state.chats.length}</h3><p class="muted">Private + Gruppenchats</p></article>
    </div>
    <div class="grid-3">
      <article class="panel card"><h4>Geplant</h4><p>${planned}</p></article>
      <article class="panel card"><h4>In Arbeit</h4><p>${progress}</p></article>
      <article class="panel card"><h4>Erledigt</h4><p>${done}</p></article>
    </div>
    <article class="panel card">
      <h4>Heute Fokus</h4>
      <p class="muted">Nutze Task Ablauf fuer schnelle Statuswechsel und Wochenplan fuer Tagesbuchung.</p>
    </article>
  `;
}

function chatsHtml() {
  const usersOptions = state.users
    .map((u) => `<option value="${u.id}">${u.full_name} (${u.email})</option>`)
    .join("");

  const chatItems = state.chats
    .map((c) => {
      const title = c.is_group ? c.name || "Gruppe" : "Privatchat";
      return `<button class="list-item chat-pick ${state.currentChatId === c.id ? "active" : ""}" data-chat-id="${c.id}">
        <div class="row between"><strong>${title}</strong> <span class="tag">${c.is_group ? "Gruppe" : "Privat"}</span></div>
      </button>`;
    })
    .join("");

  const msgItems = state.messages
    .map(
      (m) => `<div class="message"><div class="row between"><strong>${m.sender_id}</strong><small>${new Date(
        m.created_at
      ).toLocaleString()}</small></div><div>${m.content}</div></div>`
    )
    .join("");

  return `
    <div class="chat-layout">
      <article class="panel card">
        <h4>Chat Uebersicht</h4>
        <div class="list">${chatItems || "<p class='muted'>Noch keine Chats</p>"}</div>
      </article>

      <div class="list">
        <article class="panel card">
          <h4>Neuer Privatchat</h4>
          <form id="privateChatForm" class="row">
            <select name="other_user_id" required><option value="">User waehlen</option>${usersOptions}</select>
            <button class="btn subtle" type="submit">Starten</button>
          </form>
        </article>

        <article class="panel card">
          <h4>Neue Gruppe</h4>
          <form id="groupChatForm" class="form-grid">
            <label>Name<input type="text" name="name" required /></label>
            <label>Mitglieder (kommagetrennte User IDs)<input type="text" name="member_ids" placeholder="id1,id2" /></label>
            <button class="btn subtle" type="submit">Gruppe erstellen</button>
          </form>
        </article>

        <article class="panel card">
          <h4>Nachrichten</h4>
          <div class="message-list">${msgItems || "<p class='muted'>Noch keine Nachrichten</p>"}</div>
          <form id="messageForm" class="row">
            <input name="content" placeholder="Nachricht schreiben..." required />
            <button type="submit" class="btn primary">Senden</button>
          </form>
        </article>
      </div>
    </div>
  `;
}

function taskCard(t) {
  return `<article class="list-item">
    <div class="row between"><strong>${t.title}</strong><span class="tag">${t.is_shared ? "Gemeinsam" : "Privat"}</span></div>
    <p>${t.description || "-"}</p>
    <div class="row">
      <span class="tag">Plan: ${t.planned_hours ?? "-"}h</span>
      <span class="tag">Ist: ${t.actual_hours ?? "-"}h</span>
      <span class="tag">Faellig: ${t.due_date || "-"}</span>
    </div>
    <div class="row">
      <button class="btn inline subtle task-status" data-task-id="${t.id}" data-status="planned">Plan</button>
      <button class="btn inline subtle task-status" data-task-id="${t.id}" data-status="in_progress">Start</button>
      <button class="btn inline subtle task-status" data-task-id="${t.id}" data-status="done">Done</button>
      <button class="btn inline ghost task-hours" data-task-id="${t.id}">Ist-Stunden setzen</button>
    </div>
  </article>`;
}

function tasksHtml() {
  const col = (status, title) => {
    const items = state.tasks.filter((t) => t.status === status).map(taskCard).join("");
    return `<div class="task-col"><h4>${title}</h4>${items || "<p class='muted'>Leer</p>"}</div>`;
  };

  return `
    <article class="panel card">
      <h4>Neuer Task</h4>
      <form id="taskForm" class="grid-3">
        <label>Titel<input type="text" name="title" required /></label>
        <label>Assignee ID<input type="text" name="assignee_id" /></label>
        <label>Faelligkeit<input type="date" name="due_date" /></label>
        <label>Planstunden<input type="number" step="0.25" name="planned_hours" /></label>
        <label>Shared<select name="is_shared"><option value="false">Nein</option><option value="true">Ja</option></select></label>
        <label>Beschreibung<textarea name="description"></textarea></label>
        <button class="btn primary" type="submit">Task anlegen</button>
      </form>
    </article>
    <article class="panel card">
      <h4>Schneller Ablauf</h4>
      <div class="task-board">
        ${col("planned", "Geplant")}
        ${col("in_progress", "In Arbeit")}
        ${col("done", "Erledigt")}
      </div>
    </article>
  `;
}

function weekHtml() {
  const rows = state.worklogs
    .map(
      (w) => `<article class="list-item"><div class="row between"><strong>${w.work_date}</strong><span class="tag">${w.hours}h</span></div><p>${
        w.details || ""
      }</p><p class="muted">Task: ${w.task_id || "-"}</p><div class="row"><button class="btn inline ghost wk-edit" data-id="${
        w.id
      }">Bearbeiten</button><button class="btn inline danger wk-del" data-id="${w.id}">Loeschen</button></div></article>`
    )
    .join("");

  return `
    <div class="grid-2">
      <article class="panel card">
        <h4>Freigabe fuer Bearbeiter</h4>
        <form id="permForm" class="row">
          <input name="editor_id" placeholder="Editor User ID" required />
          <select name="can_edit"><option value="true">Darf editieren</option><option value="false">Nur entziehen</option></select>
          <button class="btn subtle" type="submit">Speichern</button>
        </form>
      </article>
      <article class="panel card">
        <h4>Wochenansicht</h4>
        <form id="weekFilterForm" class="row">
          <input type="date" name="week_start" value="${startOfWeek()}" required />
          <button class="btn subtle" type="submit">Laden</button>
        </form>
      </article>
    </div>

    <article class="panel card">
      <h4>Eintrag hinzufügen</h4>
      <form id="worklogForm" class="grid-3">
        <label>User ID<input name="user_id" required /></label>
        <label>Task ID<input name="task_id" /></label>
        <label>Datum<input type="date" name="work_date" required /></label>
        <label>Stunden<input type="number" step="0.25" name="hours" min="0.25" max="24" required /></label>
        <label>Details<textarea name="details"></textarea></label>
        <button class="btn primary" type="submit">Eintragen</button>
      </form>
    </article>

    <article class="panel card">
      <h4>Wochen-Einträge</h4>
      <div class="list">${rows || "<p class='muted'>Keine Eintraege</p>"}</div>
    </article>
  `;
}

function notesHtml() {
  const noteItems = state.notes
    .map(
      (n) => `<article class="list-item">
      <div class="row between"><strong>${n.title}</strong><span class="tag">${n.is_shared ? "Gemeinsam" : "Privat"}</span></div>
      <p class="note-content">${n.content}</p>
      <p class="muted">Owner: ${n.owner_id}</p>
      <div class="row">
        <button class="btn inline ghost note-edit" data-id="${n.id}">Bearbeiten</button>
        <button class="btn inline subtle note-share" data-id="${n.id}">Freigeben</button>
        <button class="btn inline danger note-del" data-id="${n.id}">Loeschen</button>
      </div>
    </article>`
    )
    .join("");

  return `
    <article class="panel card">
      <h4>Neue Notiz</h4>
      <form id="noteForm" class="grid-2">
        <label>Titel<input name="title" required /></label>
        <label>Shared<select name="is_shared"><option value="false">Nein</option><option value="true">Ja</option></select></label>
        <label>Inhalt<textarea name="content" required></textarea></label>
        <button class="btn primary" type="submit">Notiz speichern</button>
      </form>
    </article>
    <article class="panel card">
      <h4>Notizbloecke</h4>
      <div class="list">${noteItems || "<p class='muted'>Keine Notizen</p>"}</div>
    </article>
  `;
}

function usersHtml() {
  const items = state.users
    .map((u) => `<article class="list-item"><strong>${u.full_name}</strong><p>${u.email}</p><p class="muted">ID: ${u.id}</p></article>`)
    .join("");

  return `
    <article class="panel card">
      <h4>Teammitglieder</h4>
      <div class="list">${items || "<p class='muted'>Keine User gefunden</p>"}</div>
    </article>
  `;
}

function renderAll() {
  el.views.dashboard.innerHTML = dashboardHtml();
  el.views.chats.innerHTML = chatsHtml();
  el.views.tasks.innerHTML = tasksHtml();
  el.views.weekplan.innerHTML = weekHtml();
  el.views.notes.innerHTML = notesHtml();
  el.views.users.innerHTML = usersHtml();
  renderView();
  bindDynamicHandlers();
}

function bindDynamicHandlers() {
  document.querySelectorAll(".chat-pick").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.currentChatId = btn.dataset.chatId;
      await loadMessages();
      renderAll();
    });
  });

  const privateChatForm = document.getElementById("privateChatForm");
  if (privateChatForm) {
    privateChatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(privateChatForm);
      await api("/chats/private", {
        method: "POST",
        body: JSON.stringify({ other_user_id: fd.get("other_user_id") }),
      });
      await refreshCore();
      alertMsg("Privatchat erstellt");
    });
  }

  const groupChatForm = document.getElementById("groupChatForm");
  if (groupChatForm) {
    groupChatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(groupChatForm);
      const ids = String(fd.get("member_ids") || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await api("/chats/groups", {
        method: "POST",
        body: JSON.stringify({ name: fd.get("name"), member_ids: ids }),
      });
      await refreshCore();
      alertMsg("Gruppenchat erstellt");
    });
  }

  const messageForm = document.getElementById("messageForm");
  if (messageForm) {
    messageForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.currentChatId) return alertMsg("Bitte einen Chat waehlen", "err");
      const fd = new FormData(messageForm);
      await api(`/chats/${state.currentChatId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: fd.get("content") }),
      });
      messageForm.reset();
      await loadMessages();
      renderAll();
    });
  }

  const taskForm = document.getElementById("taskForm");
  if (taskForm) {
    taskForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(taskForm);
      await api("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: fd.get("title"),
          description: fd.get("description") || null,
          assignee_id: fd.get("assignee_id") || null,
          due_date: fd.get("due_date") || null,
          planned_hours: fd.get("planned_hours") ? Number(fd.get("planned_hours")) : null,
          is_shared: fd.get("is_shared") === "true",
        }),
      });
      taskForm.reset();
      await refreshCore();
      alertMsg("Task angelegt");
    });
  }

  document.querySelectorAll(".task-status").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/tasks/${btn.dataset.taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: btn.dataset.status }),
      });
      await refreshCore();
    });
  });

  document.querySelectorAll(".task-hours").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const input = window.prompt("Neue Ist-Stunden:");
      if (!input) return;
      const hours = Number(input);
      if (Number.isNaN(hours)) return alertMsg("Ungueltige Zahl", "err");
      await api(`/tasks/${btn.dataset.taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ actual_hours: hours }),
      });
      await refreshCore();
    });
  });

  const permForm = document.getElementById("permForm");
  if (permForm) {
    permForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(permForm);
      await api("/worklogs/permissions", {
        method: "POST",
        body: JSON.stringify({ editor_id: fd.get("editor_id"), can_edit: fd.get("can_edit") === "true" }),
      });
      alertMsg("Freigabe gespeichert");
    });
  }

  const weekFilterForm = document.getElementById("weekFilterForm");
  if (weekFilterForm) {
    weekFilterForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(weekFilterForm);
      await loadWeeklogs(String(fd.get("week_start")));
      renderAll();
    });
  }

  const worklogForm = document.getElementById("worklogForm");
  if (worklogForm) {
    worklogForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(worklogForm);
      await api("/worklogs", {
        method: "POST",
        body: JSON.stringify({
          user_id: fd.get("user_id"),
          task_id: fd.get("task_id") || null,
          work_date: fd.get("work_date"),
          hours: Number(fd.get("hours")),
          details: fd.get("details") || null,
        }),
      });
      worklogForm.reset();
      await refreshCore();
      alertMsg("Wochen-Eintrag gespeichert");
    });
  }

  document.querySelectorAll(".wk-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/worklogs/${btn.dataset.id}`, { method: "DELETE" });
      await refreshCore();
      alertMsg("Eintrag geloescht");
    });
  });

  document.querySelectorAll(".wk-edit").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const hours = window.prompt("Neue Stunden:");
      if (!hours) return;
      await api(`/worklogs/${btn.dataset.id}`, {
        method: "PATCH",
        body: JSON.stringify({ hours: Number(hours) }),
      });
      await refreshCore();
      alertMsg("Eintrag aktualisiert");
    });
  });

  const noteForm = document.getElementById("noteForm");
  if (noteForm) {
    noteForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(noteForm);
      await api("/notes", {
        method: "POST",
        body: JSON.stringify({
          title: fd.get("title"),
          content: fd.get("content"),
          is_shared: fd.get("is_shared") === "true",
        }),
      });
      noteForm.reset();
      await refreshCore();
      alertMsg("Notiz gespeichert");
    });
  }

  document.querySelectorAll(".note-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/notes/${btn.dataset.id}`, { method: "DELETE" });
      await refreshCore();
      alertMsg("Notiz geloescht");
    });
  });

  document.querySelectorAll(".note-edit").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const title = window.prompt("Neuer Titel (optional):") || undefined;
      const content = window.prompt("Neuer Inhalt (optional):") || undefined;
      const payload = {};
      if (title) payload.title = title;
      if (content) payload.content = content;
      await api(`/notes/${btn.dataset.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await refreshCore();
      alertMsg("Notiz aktualisiert");
    });
  });

  document.querySelectorAll(".note-share").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const userId = window.prompt("User ID fuer Freigabe:");
      if (!userId) return;
      const canEdit = window.confirm("Soll Bearbeitung erlaubt sein?");
      await api(`/notes/${btn.dataset.id}/share`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, can_edit: canEdit }),
      });
      alertMsg("Notiz freigegeben");
    });
  });
}

async function refreshCore() {
  await Promise.all([loadUsers(), loadChats(), loadTasks(), loadWeeklogs(), loadNotes()]);
  await loadMessages();
  renderAll();
}

async function bootstrapAfterLogin() {
  await loadMe();
  await refreshCore();
  el.authView.classList.add("hidden");
  el.appView.classList.remove("hidden");
}

el.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const fd = new FormData(el.loginForm);
    const body = toFormData({
      username: fd.get("email"),
      password: fd.get("password"),
      grant_type: "password",
    });
    const login = await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    setAuth(login.access_token);
    await bootstrapAfterLogin();
    alertMsg("Login erfolgreich");
  } catch (err) {
    alertMsg(`Login fehlgeschlagen: ${err.message}`, "err");
  }
});

el.registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const fd = new FormData(el.registerForm);
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: fd.get("full_name"),
        email: fd.get("email"),
        password: fd.get("password"),
      }),
    });
    el.registerForm.reset();
    alertMsg("Registrierung erfolgreich. Bitte einloggen.");
  } catch (err) {
    alertMsg(`Registrierung fehlgeschlagen: ${err.message}`, "err");
  }
});

el.logoutBtn.addEventListener("click", () => {
  setAuth("");
  state.me = null;
  el.currentUser.textContent = "Nicht eingeloggt";
  el.appView.classList.add("hidden");
  el.authView.classList.remove("hidden");
  alertMsg("Du wurdest ausgeloggt.");
});

el.apiBaseInput.addEventListener("change", () => {
  setApiBase(el.apiBaseInput.value.trim() || "http://127.0.0.1:8000/api");
  alertMsg("API URL gespeichert.");
});

el.navTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".nav-item");
  if (!btn) return;
  state.currentView = btn.dataset.view;
  renderView();
});

(async function init() {
  renderAll();
  if (!state.token) return;
  try {
    await bootstrapAfterLogin();
  } catch (err) {
    setAuth("");
    alertMsg("Session abgelaufen. Bitte neu einloggen.", "err");
  }
})();
