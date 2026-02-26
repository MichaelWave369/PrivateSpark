const state = {
  projects: [],
  projectId: null,
  models: [],
};

const el = (id) => document.getElementById(id);
const projectList = el('project-list');
const capsuleList = el('capsule-list');
const messages = el('messages');
const modelSelect = el('model-select');

async function boot() {
  await Promise.all([loadStatus(), loadProjects(), loadModels()]);
  wireEvents();
  if (state.projectId) await loadCapsules();
  addMessage('ai', 'Welcome to PrivateSpark Core. Your data stays local by default.');
}

function wireEvents() {
  el('chat-form').addEventListener('submit', submitChat);
  el('create-project').addEventListener('click', createProject);
  el('search-input').addEventListener('input', searchCapsules);
  el('export-btn').addEventListener('click', exportData);
  el('wipe-btn').addEventListener('click', wipeData);

  const dz = el('dropzone');
  dz.addEventListener('click', () => el('file-picker').click());
  dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', async (e) => {
    e.preventDefault();
    dz.classList.remove('drag');
    if (e.dataTransfer.files[0]) await uploadFile(e.dataTransfer.files[0]);
  });
  el('file-picker').addEventListener('change', async (e) => {
    if (e.target.files[0]) await uploadFile(e.target.files[0]);
  });
}

async function loadStatus() {
  const res = await fetch('/api/ollama/status');
  const data = await res.json();
  const node = el('ollama-status');
  const banner = el('setup-banner');
  if (data.ok) {
    node.className = 'status ok';
    node.textContent = '● Ollama online';
    banner.classList.add('hidden');
  } else {
    node.className = 'status warn';
    node.textContent = '● Ollama offline';
    banner.classList.remove('hidden');
    banner.textContent = 'Setup tip: install Ollama, run `ollama serve`, then `ollama pull llama3.1:latest`.';
  }
}

async function loadProjects() {
  const res = await fetch('/api/projects');
  const data = await res.json();
  state.projects = data.projects;
  if (!state.projectId && state.projects.length) state.projectId = state.projects[0].id;
  renderProjects();
}

function renderProjects() {
  projectList.innerHTML = '';
  state.projects.forEach((p) => {
    const li = document.createElement('li');
    li.textContent = p.name;
    if (p.id === state.projectId) li.classList.add('active');
    li.tabIndex = 0;
    li.onclick = async () => { state.projectId = p.id; renderProjects(); await loadCapsules(); };
    li.onkeydown = async (e) => { if (e.key === 'Enter') { state.projectId = p.id; renderProjects(); await loadCapsules(); } };
    projectList.appendChild(li);
  });
}

async function createProject() {
  const name = el('new-project-name').value.trim();
  if (!name) return;
  await fetch('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
  el('new-project-name').value = '';
  await loadProjects();
}

async function loadModels() {
  const res = await fetch('/api/models');
  const data = await res.json();
  state.models = data.models;
  modelSelect.innerHTML = '';
  if (!state.models.length) {
    const o = document.createElement('option');
    o.textContent = 'No local models found';
    o.value = '';
    modelSelect.appendChild(o);
    return;
  }
  state.models.forEach((m) => {
    const o = document.createElement('option');
    o.value = m.name;
    o.textContent = m.name;
    modelSelect.appendChild(o);
  });
}

async function submitChat(e) {
  e.preventDefault();
  const input = el('chat-input');
  const text = input.value.trim();
  if (!text || !state.projectId) return;
  addMessage('user', text);
  input.value = '';

  const payload = {
    project_id: state.projectId,
    model: modelSelect.value || null,
    temperature: 0.2,
    messages: [{ role: 'user', content: text }]
  };

  const res = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

  const ai = addMessage('ai', '');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();
    events.forEach((chunk) => {
      const event = /event: (.+)/.exec(chunk)?.[1];
      const dataRaw = /data: (.+)/.exec(chunk)?.[1];
      if (!event || !dataRaw) return;
      const data = JSON.parse(dataRaw);
      if (event === 'token') ai.textContent += data.token;
      if (event === 'error') ai.textContent = data.message;
    });
  }
}

function addMessage(role, text) {
  const node = document.createElement('div');
  node.className = `message ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

async function uploadFile(file) {
  if (!state.projectId) return;
  const form = new FormData();
  form.append('file', file);
  el('upload-status').textContent = 'Uploading…';
  const res = await fetch(`/api/files/upload?project_id=${state.projectId}`, { method: 'POST', body: form });
  const data = await res.json();
  el('upload-status').textContent = data.summary || 'Uploaded.';
  await loadCapsules();
}

async function loadCapsules() {
  const res = await fetch(`/api/projects/${state.projectId}/capsules`);
  const data = await res.json();
  renderCapsules(data.capsules);
}

function renderCapsules(capsules) {
  capsuleList.innerHTML = '';
  capsules.forEach((c) => {
    const li = document.createElement('li');
    li.textContent = `${c.title} — ${c.text.slice(0, 80)}`;
    li.tabIndex = 0;
    li.onclick = () => addMessage('ai', `Capsule: ${c.title}\n\n${c.text.slice(0, 500)}`);
    capsuleList.appendChild(li);
  });
}

async function searchCapsules(e) {
  const q = e.target.value.trim();
  if (!q || !state.projectId) return loadCapsules();
  const res = await fetch(`/api/search?project_id=${state.projectId}&q=${encodeURIComponent(q)}`);
  const data = await res.json();
  renderCapsules(data.results || []);
}

async function exportData() {
  const res = await fetch('/api/privacy/export', { method: 'POST' });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'privatespark-export.zip';
  a.click();
  URL.revokeObjectURL(url);
}

async function wipeData() {
  const ok = window.prompt('Type WIPE_MY_DATA to confirm local wipe');
  if (ok !== 'WIPE_MY_DATA') return;
  await fetch('/api/privacy/wipe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm_token: ok })
  });
  await loadProjects();
  await loadCapsules();
  addMessage('ai', 'Local data wiped and reset complete.');
}

boot();
