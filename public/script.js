/*
Developer notes (public/script.js)
- Main responsibilities: rendering messages, handling composer actions, managing localStorage, theme toggle, and calling `/api/mcp`.
- Key functions:
  - renderMessage(msg): creates DOM nodes for each message. Avatars can be changed here.
  - addLocalMessage(text, who): appends to `chat[]` and persists to localStorage (key: 'chat_messages').
  - showTyping()/removeTyping(): typing indicator DOM.
  - setFetching(state): disables input and shows spinner while awaiting server response.
- Keep accessibility in mind: `.messages` has role="log" and aria-live="polite".
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

async function parseJsonSafe(res) {
  const text = await res.text();
  try {
    return { data: JSON.parse(text), text };
  } catch (e) {
    return { data: null, text };
  }
}

function getApiUrl() {
  const origin = window.location.origin;
  if (!origin || origin === 'null') return '/api/mcp';
  return `${origin}/api/mcp`;
}

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

function autoResize() {
  // keep it scrollable; only grow up to a max height
  input.style.height = 'auto';
  const max = 160; // px
  const next = Math.min(input.scrollHeight, max);
  input.style.height = `${next}px`;
  input.style.overflowY = input.scrollHeight > max ? 'auto' : 'hidden';
}

// Load existing messages
load();
if (chat.length){
  chat.forEach(renderMessage);
} else {
  const welcomeMsg = `Welcome! I can help you manage events and plan projects.

What would you like to accomplish?

You can also use commands like:
• "list" — show all events
• "Add Birthday on 2026-02-01" — add an event
• "Add Meeting on 2026-02-01 at 14:30" — add a timed event
• "summarize" — get a summary of upcoming events
• "delete:EventTitle" — remove an event`;
  addLocalMessage(welcomeMsg, 'bot');
  messages.scrollTop = messages.scrollHeight;
}

// accessibility: focus input on load
window.addEventListener('load', ()=> input.focus());
  
  // OAuth sign-in helpers
  async function startOauth(provider) {
    try {
      const resp = await fetch(getApiUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'oauth_login', input: { provider } })
      });
      const { data, text } = await parseJsonSafe(resp);
      if (!resp.ok) {
        showBanner((data && data.error) ? JSON.stringify(data.error) : (text || `Error ${resp.status}`), 'error');
        return;
      }
      const result = data?.result;
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
  // Re-show welcome message with planning trigger
  const welcomeMsg = `Welcome! I can help you manage events and plan projects.

What would you like to accomplish?

You can also use commands like:
• "list" — show all events
• "Add Birthday on 2026-02-01" — add an event
• "Add Meeting on 2026-02-01 at 14:30" — add a timed event
• "summarize" — get a summary of upcoming events
• "delete:EventTitle" — remove an event`;
  addLocalMessage(welcomeMsg, 'bot');
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
    const res = await fetch(getApiUrl(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: 'handle_message', input: { message: text } })
    });

    const { data, text: rawText } = await parseJsonSafe(res);
    removeTyping();

    if (res.ok && data && data.result) {
      addLocalMessage(data.result, 'bot');
    } else {
      addLocalMessage(`Error (${res.status}): ` + (data?.error || rawText || JSON.stringify(data)), 'bot');
    }
  } catch (err) {
    removeTyping();
    addLocalMessage('Network error: ' + err.message, 'bot');
  } finally {
    setFetching(false);
  }
});

// helper: render a recurrence prompt below the last bot message
function showRecurrencePrompt(title){
  const promptEl = document.createElement('div');
  promptEl.className = 'message bot';
  promptEl.innerHTML = `
    <div class="avatar">⭐</div>
    <div class="bubble">
      <div class="text">Would you like reminders for "<strong>${escapeHtml(title)}</strong>"?</div>
      <div class="meta" style="margin-top:8px; gap:6px;">
        <button class="copy rec-btn" data-f="none">No reminders</button>
        <button class="copy rec-btn" data-f="daily">Every day</button>
        <button class="copy rec-btn" data-f="every_other_day">Every other day</button>
        <button class="copy rec-btn" data-f="weekly">Weekly</button>
        <button class="copy rec-btn" data-f="biweekly">Every two weeks</button>
        <button class="copy rec-btn" data-f="weekdays">Weekdays (Mon–Fri)</button>
        <button class="copy rec-btn" data-f="monthly">Monthly (same day)</button>
        <button class="copy rec-btn" data-f="monthly_on_day">Monthly on day...</button>
        <button class="copy rec-btn" data-f="custom">Custom interval</button>
      </div>
    </div>
  `;
  messages.appendChild(promptEl);
  messages.scrollTop = messages.scrollHeight;

  // attach handlers
  promptEl.querySelectorAll('.rec-btn').forEach(btn=>{
    btn.addEventListener('click', async (e)=>{
      const freq = e.currentTarget.dataset.f;
      let interval = 1;

      if (freq === 'monthly_on_day'){
        const ans = prompt('Enter day of month (1-31) for monthly_on_day:');
        if (!ans) return;
        const num = parseInt(ans,10);
        if (isNaN(num) || num < 1 || num > 31){
          alert('Invalid day. Please enter 1-31.');
          return;
        }
        interval = num;
      } else if (freq === 'custom'){
        const ans = prompt('Enter a numeric interval (e.g., "3" for every 3 days):');
        if (!ans) return;
        const num = parseInt(ans,10);
        if (isNaN(num) || num < 1){
          alert('Invalid interval; must be positive integer.');
          return;
        }
        interval = num;
      }

      // call server tool set_recurrence
      setFetching(true);
      try {
        const resp = await fetch(getApiUrl(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool: 'set_recurrence', input: { title, frequency: freq, interval } })
        });
        const { data, text: rawText } = await parseJsonSafe(resp);
        if (resp.ok && data?.result){
          addLocalMessage(data.result, 'bot');
        } else {
          addLocalMessage('Error setting recurrence: ' + (data?.error || rawText || JSON.stringify(data)), 'bot');
        }
      } catch (err){
        addLocalMessage('Network error: ' + err.message, 'bot');
      } finally {
        setFetching(false);
      }
      // remove the prompt element
      promptEl.remove();
    });
  });
}

// Client helpers for the project planning flow

async function submitProjectGoal(goalText) {
  // prompt user for deadline
  const deadline = prompt('When would you like this done by? (YYYY-MM-DD)');
  if (deadline === null) return; // user canceled
  const deadlineTrim = deadline.trim();
  if (!deadlineTrim) {
    addLocalMessage('Please enter a deadline in YYYY-MM-DD to continue.', 'bot');
    return;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(deadlineTrim)) {
    addLocalMessage('Invalid deadline format. Use YYYY-MM-DD (e.g., 2026-03-05).', 'bot');
    return;
  }
  addLocalMessage(goalText, 'user');
  addLocalMessage('Working on a plan…', 'bot');

  try {
    const res = await fetch(getApiUrl(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: 'research_and_breakdown', input: { goal: goalText, deadline: deadlineTrim } })
    });
    const { data, text: rawText } = await parseJsonSafe(res);
    if (res.ok && data?.result) {
      let plan = data.result;
      // If plan is a string (shouldn't happen with the fix, but handle it), try to parse it
      if (typeof plan === 'string') {
        try {
          plan = JSON.parse(plan);
        } catch (e) {
          addLocalMessage('Error parsing plan: ' + plan, 'bot');
          return;
        }
      }
      // Validate plan structure
      if (!plan || !plan.milestones || !Array.isArray(plan.milestones)) {
        addLocalMessage('Invalid plan format received: ' + JSON.stringify(plan), 'bot');
        return;
      }
      // render plan as bot message with milestones and cadence suggestions
      const lines = [];
      lines.push(`Plan for "${plan.goal}" (deadline: ${plan.deadline || 'not specified'}):`);
      plan.milestones.forEach((m, i) => {
        lines.push(`${i+1}. ${m.title} — due ${m.due}`);
        if (Array.isArray(m.steps) && m.steps.length) {
          m.steps.forEach((step) => {
            if (step && String(step).trim()) {
              lines.push(`   - ${String(step).trim()}`);
            }
          });
        }
      });
      lines.push('Suggested cadences: ' + (plan.cadence_suggestions || []).join(', '));
      addLocalMessage(lines.join('\n'), 'bot');

      // show quick action: "Create tasks" prompt (simple)
      const createBtn = document.createElement('button');
      createBtn.textContent = 'Create tasks from plan';
      createBtn.className = 'copy';
      createBtn.addEventListener('click', async () => {
        // call server tool to create tasks from the plan
        setFetching(true);
        try {
          const resp = await fetch(getApiUrl(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: 'create_tasks', input: plan })
          });
          const { data: taskData, text: taskText } = await parseJsonSafe(resp);
          if (resp.ok && taskData?.result) {
            addLocalMessage(taskData.result, 'bot');
          } else {
            addLocalMessage('Failed to create tasks: ' + (taskData?.error || taskText || JSON.stringify(taskData)), 'bot');
          }
        } catch (err) {
          addLocalMessage('Network error creating tasks: ' + err.message, 'bot');
        } finally {
          setFetching(false);
        }
       });
      // append to messages area
      const wrapper = document.createElement('div');
      wrapper.className = 'message bot';
      wrapper.appendChild(createBtn);
      messages.appendChild(wrapper);
      messages.scrollTop = messages.scrollHeight;
    } else {
      addLocalMessage('Failed to generate plan: ' + (data?.error || rawText || JSON.stringify(data)), 'bot');
    }
  } catch (err) {
    addLocalMessage('Network error when generating plan: ' + err.message, 'bot');
  }
}

// wire quick shortcut: when bot asks "what would you like to accomplish?" show a small quick-prompt UI
function interceptGoalPrompt(text) {
  // called after adding a bot message; keep it tiny: show a "Start Project" suggestion that when clicked prompts user
  if (/what would you like to accomplish\?/i.test(text)) {
    const quick = document.createElement('div');
    quick.className = 'quick-actions';
    quick.innerHTML = `<p style="margin:4px 0;font-size:0.9em;color:var(--muted);">👇 Click the button below to start planning your project</p><button class="copy" id="startProjectBtn">Start Project</button>`;
    messages.appendChild(quick);
    document.getElementById('startProjectBtn').addEventListener('click', () => {
      const goal = prompt('Briefly describe the goal you want to accomplish (one sentence):');
      if (!goal) return;
      submitProjectGoal(goal);
      quick.remove();
    });
    messages.scrollTop = messages.scrollHeight;
  }
}

// modify addLocalMessage to call interceptGoalPrompt when bot messages are added
const _addLocalMessage = addLocalMessage;
addLocalMessage = function(text, who) {
  _addLocalMessage(text, who);
  if (who === 'bot') interceptGoalPrompt(text);
};

/*
Project-planning flow developer notes
- Purpose: lightweight client-side helpers that let the bot prompt the user for a high-level goal,
  call the server tool `research_and_breakdown(goal, deadline)` to get a structured plan,
  and optionally call `create_tasks(plan)` server tool to create calendar tasks.
- Key client functions to edit:
  - submitProjectGoal(goalText)
      * Prompts user for a deadline, sends the goal to /api/mcp tool 'research_and_breakdown'
      * Renders the returned plan and exposes a "Create tasks from plan" quick action.
      * To change where the deadline is requested (inline UI vs prompt), modify this function.
  - interceptGoalPrompt(text)
      * Detects the bot prompt "What would you like to accomplish?" and injects a small quick-action
        button that opens the project flow. Edit the regex or UI here to change trigger text or styling.
  - The quick "Create tasks" action calls the server-side tool 'create_tasks' with the plan payload.
      * Server-side: see main.py tools `research_and_breakdown` and `create_tasks`.
      * To change persistence (DB/KV), update the server-side `create_tasks` implementation.
- Extensibility notes:
  - If integrating an LLM client on the browser, prefer doing that server-side and keep the client minimal.
  - To add UX improvements (deadline datepicker, cadence selector), replace the prompt() calls with
    a small modal/dialog component and bind its values into the payload sent to /api/mcp.
  - Client-side validation: submitProjectGoal currently assumes the server will validate the deadline string.
    Add client-side validation for YYYY-MM-DD or use a date picker.
- Files to update for full flow:
  - server: main.py (tools: research_and_breakdown, create_tasks, set_recurrence)
  - client: public/script.js (submitProjectGoal, interceptGoalPrompt)
  - UI: public/index.html (optional UI elements for project flow)
  - docs: README.md / DEVELOPING.md (update instructions if you change tool names)

*/
