const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const messages = document.getElementById('messages');
const dropzone = document.getElementById('dropzone');
const dropResult = document.getElementById('drop-result');

chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage(text, 'user');
  chatInput.value = '';

  setTimeout(() => {
    addMessage(
      "Local assistant: I can summarize files, generate drafts, transcribe audio, and keep everything private on this device.",
      'ai'
    );
  }, 300);
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (event) => {
  const files = Array.from(event.dataTransfer.files || []);
  if (!files.length) {
    dropResult.textContent = 'No valid files detected.';
    return;
  }

  dropResult.textContent = `Ready to analyze: ${files.map((file) => file.name).join(', ')}`;
});

function addMessage(text, role) {
  const message = document.createElement('div');
  message.className = `message ${role}`;
  message.textContent = text;
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
}
