/*
Developer notes (public/script.js)
- Main responsibilities: rendering messages, handling composer actions, managing localStorage, theme toggle, and calling `/api/mcp`.
- Key functions:
  - renderMessage(msg): creates DOM nodes for each message. Avatars can be changed here.
  - addLocalMessage(text, who): appends to `chat[]` and persists to localStorage (key: 'chat_messages').
  - showTyping()/removeTyping(): typing indicator DOM.
  - setFetching(state): disables input and shows spinner while awaiting server response.
- Keep accessibility in mind: `.messages` has role="log" and aria-live="polite`.
*/

/* === Sections ===
 - Initialization & DOM refs
 - Storage helpers (save/load)
 - Theme helpers (setTheme, loadTheme)
 - Rendering helpers (renderMessage, addLocalMessage)
 - Composer and network (form submit)
 - OAuth / test sign-in helpers
*/

const form = document.getElementById('form');
const input = document.getElementById('input'); // textarea
const messages = document.getElementById('messages');
const spinner = document.getElementById('spinner');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const clearBtnTop = document.getElementById('clearBtnTop');
const themeToggle = document.getElementById('themeToggle');

let chat = [] // persisted messages
let typingEl = null

function save() {
  try {
    localStorage.setItem('chat_messages', JSON.stringify(chat));
  } catch (e) {
    console.warn('localStorage save failed', e);
  }
}

function load() {
  try {
    chat = JSON.parse(localStorage.getItem('chat_messages') || '[]');
  } catch (e) {
    chat = [];
  }
}

// Theme
function setTheme(t){
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('ui_theme', t);
  // update toggle icon and label
  if (t === 'dark'){
    themeToggle.textContent = '☀️';
    themeToggle.setAttribute('aria-label','Switch to light theme');
  } else {
    themeToggle.textContent = '🌙';
    themeToggle.setAttribute('aria-label','Switch to dark theme');
  }
  // adjust text color in light mode
  if (t === 'light'){
    document.documentElement.style.color = '#071429';
  } else {
    document.documentElement.style.color = '';
  }
}

function loadTheme(){
  const t = localStorage.getItem('ui_theme') || 'light';
  setTheme(t);
}

loadTheme();

function escapeHtml(str){
  return str.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
}

function formatTime(ts){
  try { return new Date(ts).toLocaleString(); } catch(e){ return '' }
}

function renderMessage(msg){
  const el = document.createElement('div');
  el.className = 'message ' + (msg.who === 'user' ? 'user' : 'bot') + ' enter';
  el.innerHTML = `
    <div class="avatar">${msg.who === 'user' ? '🌞' : '⭐'}</div>
    <div class="bubble">
      <div class="text">${escapeHtml(msg.text)}</div>
      <div class="meta">
        <time>${formatTime(msg.ts)}</time>
        <button class="copy" aria-label="Copy message">Copy</button>
      </div>
    </div>
  `;
  messages.appendChild(el);
  // trigger enter animation
  requestAnimationFrame(()=> el.classList.remove('enter'));
  messages.scrollTop = messages.scrollHeight;
}

function addLocalMessage(text, who='user'){
  const m = { who, text, ts: Date.now() };
  chat.push(m);
  save();
  renderMessage(m);
}

function showTyping(){
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'message bot typing';
  typingEl.innerHTML = `
    <div class="avatar">⭐</div>
    <div class="bubble"><div class="dots"><span></span><span></span><span></span></div></div>
  `;
  messages.appendChild(typingEl);
  messages.scrollTop = messages.scrollHeight;
}

function removeTyping(){
  if (typingEl){
    typingEl.remove();
    typingEl = null;
  }
}

function setFetching(state){
  if (state){
    spinner.hidden = false;
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.setAttribute('aria-busy','true');
  } else {
    spinner.hidden = true;
    input.disabled = false;
    sendBtn.disabled = false;
    sendBtn.removeAttribute('aria-busy');
    input.focus();
  }
}

function autoResize(){
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
}

// Load existing messages
load();
if (chat.length){
  chat.forEach(renderMessage);
} else {
  addLocalMessage('Welcome! Try commands: list, summarize, add:Title|YYYY-MM-DD|Desc, delete:Title', 'bot');
}

// accessibility: focus input on load
window.addEventListener('load', ()=> input.focus());
  
  // OAuth sign-in helpers
  async function startOauth(provider) {
    try {
      const resp = await fetch('/api/mcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'oauth_login', input: { provider } })
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        showBanner((body && body.error) ? JSON.stringify(body.error) : `Error ${resp.status}` , 'error');
        return;
      }
      const result = body.result;
      const url = (typeof result === 'string') ? result : (result?.auth_url || result?.url || result?.redirect_url);
      if (url) {
        // perform a top-level redirect to avoid popup blocking
        window.location.href = url;
        return;
      }
      showBanner('No authentication URL returned by server', 'error');
    } catch (err) {
      console.error('OAuth start failed', err);
      showBanner('Failed to start authentication', 'error');
    }
  }

  const gbtn = document.getElementById('signinGoogle');
  const mbtn = document.getElementById('signinMicrosoft');
  // For testing locally we provide a simple test handler that doesn't perform OAuth.
  function testSignIn(provider){
    console.log('Sign-in clicked:', provider);
    addLocalMessage(`${provider} sign-in clicked`, 'user');
    addLocalMessage(`(Test) Simulated auth response for ${provider}.`, 'bot');
    // small delay so messages render before navigation
    setTimeout(() => {
      if (provider === 'Google') {
        window.location.href = '/redirect_google.html';
      } else if (provider === 'Microsoft') {
        // direct to Microsoft domain per request
        window.location.href = 'https://www.microsoft.com';
      } else {
        window.location.href = 'https://www.google.com';
      }
    }, 700);
  }

  if (gbtn) gbtn.addEventListener('click', () => testSignIn('Google'));
  if (mbtn) mbtn.addEventListener('click', () => testSignIn('Microsoft'));

// Keep theme set when page loads
loadTheme();

// Event delegation for copy buttons
messages.addEventListener('click', (e) => {
  const btn = e.target.closest('.copy');
  if (!btn) return;
  const bubble = btn.closest('.bubble');
  const text = bubble.querySelector('.text').textContent;
  navigator.clipboard?.writeText(text).then(() => {
    btn.textContent = 'Copied';
    setTimeout(() => btn.textContent = 'Copy', 1200);
  }).catch(() => {
    btn.textContent = 'Fail';
    setTimeout(() => btn.textContent = 'Copy', 1200);
  });
});

// Clear conversation
function clearConversation(){
  if (!confirm('Clear conversation?')) return;
  chat = [];
  save();
  messages.innerHTML = '';
  addLocalMessage('Conversation cleared.');
}
clearBtn?.addEventListener('click', clearConversation);
clearBtnTop?.addEventListener('click', clearConversation);

// Theme toggle
themeToggle?.addEventListener('click', ()=>{
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  setTheme(cur === 'dark' ? 'light' : 'dark');
});

// Keyboard: Enter to send, Shift+Enter for newline
input.addEventListener('keydown', (e)=>{
  if (e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener('input', autoResize);

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addLocalMessage(text, 'user');
  input.value = '';
  autoResize();

  setFetching(true);
  showTyping();

  try {
    const res = await fetch('/api/mcp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: 'handle_message', input: { message: text } })
    });

    const data = await res.json();
    removeTyping();

    if (res.ok && data && data.result) {
      addLocalMessage(data.result, 'bot');
    } else {
      addLocalMessage('Error: ' + (data?.error || JSON.stringify(data)), 'bot');
    }
  } catch (err) {
    removeTyping();
    addLocalMessage('Network error: ' + err.message, 'bot');
  } finally {
    setFetching(false);
  }
});
