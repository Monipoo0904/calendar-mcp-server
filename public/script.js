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

function logPlanClient(level, message, details = null) {
  const prefix = `[plan-client][${level}] ${message}`;
  if (details === null || details === undefined) {
    console.log(prefix);
    return;
  }
  if (level === 'ERROR' || level === 'WARN') {
    console.error(prefix, details);
    return;
  }
  console.log(prefix, details);
}

function getApiUrl() {
  const origin = window.location.origin;
  if (!origin || origin === 'null') return '/api/mcp';
  return `${origin}/api/mcp`;
}

function exportCalendarIcs() {
  const origin = window.location.origin;
  const url = (!origin || origin === 'null') ? '/export.ics' : `${origin}/export.ics`;
  const a = document.createElement('a');
  a.href = url;
  a.download = 'events.ics';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function exportMilestonesIndividually(milestones) {
  if (!milestones || !milestones.length) {
    exportCalendarIcs();
    return;
  }
  const origin = window.location.origin;
  const base = (!origin || origin === 'null') ? '' : origin;
  for (let i = 0; i < milestones.length; i++) {
    const m = milestones[i];
    const title = m.title || `Milestone ${i + 1}`;
    const url = `${base}/export-single.ics?title=${encodeURIComponent(title)}`;
    const a = document.createElement('a');
    a.href = url;
    const safeName = title.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase().slice(0, 40);
    a.download = `milestone_${i + 1}_${safeName}.ics`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    if (i < milestones.length - 1) {
      await new Promise(r => setTimeout(r, 500));
    }
  }
}

function showIcsExportButton(message = 'Ready to export your calendar file?', milestones = null) {
  const actionEl = document.createElement('div');
  actionEl.className = 'message bot';
  actionEl.innerHTML = `
    <div class="avatar">⭐</div>
    <div class="bubble">
      <div class="text">${escapeHtml(message)}</div>
      <div class="meta" style="margin-top:8px;">
        <button class="copy export-ics-btn plan-primary-btn">Export .ics</button>
      </div>
    </div>
  `;
  messages.appendChild(actionEl);
  messages.scrollTop = messages.scrollHeight;

  const exportBtn = actionEl.querySelector('.export-ics-btn');
  exportBtn?.addEventListener('click', async () => {
    logPlanClient('INFO', 'Inline .ics export requested');
    if (milestones && milestones.length) {
      await exportMilestonesIndividually(milestones);
      addLocalMessage(`Downloading ${milestones.length} calendar invite(s) — one per milestone.`, 'bot');
    } else {
      exportCalendarIcs();
      addLocalMessage('Downloading .ics export now.', 'bot');
    }
  });
}

function looksLikeStudentPlanRequest(text) {
  return /lesson\s*plans?|student\s*plans?|student\s*skills?|strengths?|personalized\s*lesson/i.test(text || '');
}

function extractRequestedStudentNames(text) {
  const m = String(text || '').match(/\bfor\s+(.+)$/i);
  if (!m) return '';
  return m[1].trim().replace(/[.!?]+$/, '');
}

async function submitPersonalizedLessonPlans(userText) {
  const requestedStudents = extractRequestedStudentNames(userText);
  try {
    const res = await fetch(getApiUrl(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool: 'personalized_lesson_plans',
        input: {
          students: requestedStudents,
          lesson_goal: '',
          max_students: 12,
        }
      })
    });
    const { data, text: rawText } = await parseJsonSafe(res);
    if (res.ok && data?.result) {
      const result = data.result;
      if (typeof result === 'string') {
        addLocalMessage(result, 'bot');
        return;
      }
      if (result?.summary) {
        addLocalMessage(result.summary, 'bot');
        showStudentCalendarActions(result);
        return;
      }
      addLocalMessage('Personalized lesson plans generated, but the response format was unexpected.', 'bot');
      return;
    }
    addLocalMessage(`Error (${res.status}): ` + (data?.error || rawText || JSON.stringify(data)), 'bot');
  } catch (err) {
    addLocalMessage('Network error: ' + err.message, 'bot');
  }
}

function showScrollableStudentSelector(students) {
  return new Promise((resolve) => {
    if (!Array.isArray(students) || !students.length) {
      resolve(null);
      return;
    }

    const pickerEl = document.createElement('div');
    pickerEl.className = 'message bot';
    pickerEl.innerHTML = `
      <div class="avatar">⭐</div>
      <div class="bubble">
        <div class="text">Select the student from the list (scroll to find the right name):</div>
        <div class="meta" style="margin-top:8px; display:block;">
          <select class="student-scroll-picker" size="8" style="width:100%; max-height:220px; overflow-y:auto; border-radius:8px; padding:8px;">
            ${students.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
          </select>
          <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
            <button class="copy confirm-student-btn plan-primary-btn">Use Selected Student</button>
            <button class="copy cancel-student-btn">Cancel</button>
          </div>
        </div>
      </div>
    `;
    messages.appendChild(pickerEl);
    messages.scrollTop = messages.scrollHeight;

    const selectEl = pickerEl.querySelector('.student-scroll-picker');
    const confirmBtn = pickerEl.querySelector('.confirm-student-btn');
    const cancelBtn = pickerEl.querySelector('.cancel-student-btn');

    confirmBtn?.addEventListener('click', () => {
      const selectedName = selectEl?.value || '';
      pickerEl.remove();
      resolve(selectedName || null);
    });

    cancelBtn?.addEventListener('click', () => {
      pickerEl.remove();
      resolve(null);
    });
  });
}

async function fetchLessonPlanForStudent(studentName) {
  const res = await fetch(getApiUrl(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tool: 'personalized_lesson_plans',
      input: {
        students: studentName,
        lesson_goal: '',
        max_students: 1,
      }
    })
  });
  const { data, text: rawText } = await parseJsonSafe(res);
  if (!res.ok || !data?.result) {
    throw new Error(data?.error || rawText || `Failed to fetch lesson plan (${res.status})`);
  }
  const result = data.result;
  const plans = Array.isArray(result?.lesson_plans) ? result.lesson_plans : [];
  return plans[0] || null;
}

function buildCalendarPlanFromStudentLesson(selectedPlan, startDateStr, cadenceDays) {
  const start = new Date(`${startDateStr}T09:00:00`);
  const strengths = (selectedPlan?.strengths || []).join(', ');
  const sessions = Array.isArray(selectedPlan?.sessions) ? selectedPlan.sessions : [];

  const milestones = sessions.map((session, index) => {
    const dueDate = new Date(start);
    dueDate.setDate(start.getDate() + (index * cadenceDays));
    const due = dueDate.toISOString().slice(0, 10);
    const activities = Array.isArray(session?.activities) ? session.activities : [];
    const objective = session?.objective ? String(session.objective).trim() : '';
    const descriptionParts = [];
    if (objective) descriptionParts.push(`Objective: ${objective}`);
    if (strengths) descriptionParts.push(`Strengths: ${strengths}`);

    return {
      title: `${selectedPlan.student} - ${session?.title || `Session ${index + 1}`}`,
      due,
      description: descriptionParts.join('\n'),
      steps: activities,
    };
  });

  return {
    goal: `Personalized lesson plan for ${selectedPlan?.student || 'student'}`,
    deadline: milestones.length ? milestones[milestones.length - 1].due : startDateStr,
    milestones,
  };
}

function showStudentCalendarActions(result) {
  const lessonPlans = Array.isArray(result?.lesson_plans) ? result.lesson_plans : [];
  const availableStudents = Array.isArray(result?.available_students) ? result.available_students : lessonPlans.map((p) => p.student).filter(Boolean);
  if (!availableStudents.length) return;

  const studentsText = availableStudents.join(', ');
  const actionEl = document.createElement('div');
  actionEl.className = 'message bot';
  actionEl.innerHTML = `
    <div class="avatar">⭐</div>
    <div class="bubble">
      <div class="text">Choose a student and add their personalized lesson sessions to the calendar.\nStudents: ${escapeHtml(studentsText)}</div>
      <div class="meta" style="margin-top:8px;">
        <button class="copy create-student-calendar-btn plan-primary-btn">Choose Student + Create Calendar Tasks</button>
      </div>
    </div>
  `;
  messages.appendChild(actionEl);
  messages.scrollTop = messages.scrollHeight;

  const createBtn = actionEl.querySelector('.create-student-calendar-btn');
  createBtn?.addEventListener('click', async () => {
    const selectedStudent = await showScrollableStudentSelector(availableStudents);
    if (!selectedStudent) return;

    let selectedPlan = lessonPlans.find((p) => p.student === selectedStudent);
    if (!selectedPlan) {
      try {
        selectedPlan = await fetchLessonPlanForStudent(selectedStudent);
      } catch (err) {
        addLocalMessage('Could not load lesson plan for that student: ' + err.message, 'bot');
        return;
      }
    }
    if (!selectedPlan) return;

    const today = new Date().toISOString().slice(0, 10);
    const startDateRaw = prompt(
      `Start date for ${selectedPlan.student}'s lesson sequence (YYYY-MM-DD):`,
      today
    );
    if (startDateRaw === null) return;
    const startDate = String(startDateRaw).trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      addLocalMessage('Invalid date format. Use YYYY-MM-DD.', 'bot');
      return;
    }

    const cadenceRaw = prompt('Spacing between sessions in days (default 7):', '7');
    if (cadenceRaw === null) return;
    const cadenceDays = parseInt(String(cadenceRaw).trim() || '7', 10);
    if (!Number.isInteger(cadenceDays) || cadenceDays < 1 || cadenceDays > 30) {
      addLocalMessage('Invalid cadence. Enter a whole number between 1 and 30.', 'bot');
      return;
    }

    const plan = buildCalendarPlanFromStudentLesson(selectedPlan, startDate, cadenceDays);
    if (!plan.milestones.length) {
      addLocalMessage(`No lesson sessions found for ${selectedPlan.student}.`, 'bot');
      return;
    }

    setFetching(true);
    try {
      const resp = await fetch(getApiUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'create_tasks', input: { plan } })
      });
      const { data: taskData, text: taskText } = await parseJsonSafe(resp);
      if (resp.ok && taskData?.result) {
        addLocalMessage(taskData.result, 'bot');
        showIcsExportButton(`Ready to export ${selectedPlan.student}'s lesson sessions as .ics files?`, plan.milestones);
      } else {
        addLocalMessage('Failed to create student lesson tasks: ' + (taskData?.error || taskText || JSON.stringify(taskData)), 'bot');
      }
    } catch (err) {
      addLocalMessage('Network error while creating student lesson tasks: ' + err.message, 'bot');
    } finally {
      setFetching(false);
    }
  });
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
  const welcomeMsg = `What would you like to accomplish? (Describe your goal and I'll help you plan it out.)`;
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
  const welcomeMsg = `What would you like to accomplish? (Describe your goal and I'll help you plan it out.)`;
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
    if (looksLikeStudentPlanRequest(text)) {
      removeTyping();
      await submitPersonalizedLessonPlans(text);
      return;
    }

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
  logPlanClient('INFO', 'Starting project plan flow', { goal: goalText });
  // prompt user for deadline
  const deadline = prompt('When would you like this done by? (YYYY-MM-DD)');
  if (deadline === null) return; // user canceled
  const deadlineTrim = deadline.trim();
  if (!deadlineTrim) {
    logPlanClient('WARN', 'Deadline was empty');
    addLocalMessage('Please enter a deadline in YYYY-MM-DD to continue.', 'bot');
    return;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(deadlineTrim)) {
    logPlanClient('WARN', 'Deadline format invalid', { deadline: deadlineTrim });
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
      logPlanClient('INFO', 'Received planning response', { resultType: typeof plan });
      // If plan is a string (shouldn't happen with the fix, but handle it), try to parse it
      if (typeof plan === 'string') {
        try {
          plan = JSON.parse(plan);
        } catch (e) {
          logPlanClient('ERROR', 'Failed to parse string plan result', { rawPlan: plan });
          addLocalMessage('Error parsing plan: ' + plan, 'bot');
          return;
        }
      }
      // Validate plan structure
      if (!plan || !plan.milestones || !Array.isArray(plan.milestones)) {
        logPlanClient('ERROR', 'Plan missing milestones array', plan);
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

      // show quick action: "Create tasks" prompt with cadence and reminder options
      const actionEl = document.createElement('div');
      actionEl.className = 'message bot';
      actionEl.innerHTML = `
        <div class="avatar">⭐</div>
        <div class="bubble">
          <div class="text">Ready to prepare a calendar export for this plan?</div>
          <div class="meta" style="margin-top:8px;">
            <button class="copy create-tasks-btn plan-primary-btn">Prepare export</button>
          </div>
        </div>
      `;
      messages.appendChild(actionEl);
      messages.scrollTop = messages.scrollHeight;

      const createBtn = actionEl.querySelector('.create-tasks-btn');

      createBtn.addEventListener('click', async () => {
        const exportWhereRaw = prompt(
          'Where do you want to export this plan?\n\n' +
          'Type one:\n' +
          '- google\n' +
          '- microsoft\n' +
          '- ics\n\n' +
          'Default is ics.'
        );
        if (exportWhereRaw === null) return;
        const exportWhere = (exportWhereRaw || 'ics').trim().toLowerCase() || 'ics';

        const exportWhenRaw = prompt(
          'When should the export happen?\n\n' +
          'Type one:\n' +
          '- now\n' +
          '- after review\n\n' +
          'Default is now.'
        );
        if (exportWhenRaw === null) return;
        const exportWhen = (exportWhenRaw || 'now').trim().toLowerCase() || 'now';

        // Ask for cadence preference
        const cadenceChoice = prompt(
          'Choose a reminder cadence for milestone check-ins:\n\n' +
          '1 - Daily\n' +
          '2 - Weekly\n' +
          '3 - Biweekly\n' +
          '4 - Monthly\n' +
          '5 - None (no reminders)\n\n' +
          'Enter 1-5:'
        );
        
        if (cadenceChoice === null) return; // user canceled
        
        const cadenceMap = {
          '1': 'daily',
          '2': 'weekly', 
          '3': 'biweekly',
          '4': 'monthly',
          '5': 'none'
        };
        
        const selectedCadence = cadenceMap[cadenceChoice?.trim()] || 'none';
        
        // Ask if they want calendar reminders
        const wantsReminders = confirm(
          'Would you like to add calendar reminders for each milestone?\n\n' +
          'Click OK to add reminders, or Cancel to skip.'
        );

        const confirmEl = document.createElement('div');
        confirmEl.className = 'message bot';
        confirmEl.innerHTML = `
          <div class="avatar">⭐</div>
          <div class="bubble">
            <div class="text">Review export settings:\n• Where: ${escapeHtml(exportWhere)}\n• When: ${escapeHtml(exportWhen)}\n• Reminders: ${wantsReminders ? escapeHtml(selectedCadence) : 'none'}</div>
            <div class="meta" style="margin-top:8px;">
              <button class="copy confirm-export-btn plan-primary-btn">Confirm export</button>
            </div>
          </div>
        `;
        messages.appendChild(confirmEl);
        messages.scrollTop = messages.scrollHeight;

        const confirmBtn = confirmEl.querySelector('.confirm-export-btn');
        if (!confirmBtn) return;

        confirmBtn.addEventListener('click', async () => {
          confirmBtn.disabled = true;
          confirmBtn.textContent = 'Exporting…';
        
          // call server tool to create tasks from the plan
          setFetching(true);
          try {
            const resp = await fetch(getApiUrl(), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tool: 'create_tasks', input: { plan } })
            });
            const { data: taskData, text: taskText } = await parseJsonSafe(resp);
            if (resp.ok && taskData?.result) {
              logPlanClient('INFO', 'create_tasks succeeded');
              addLocalMessage(taskData.result, 'bot');
            
              // If user wants reminders and selected a cadence, set recurrence for each milestone
              if (wantsReminders && selectedCadence !== 'none') {
                for (const milestone of plan.milestones) {
                  try {
                    const recResp = await fetch(getApiUrl(), {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ 
                        tool: 'set_recurrence', 
                        input: { 
                          title: milestone.title, 
                          frequency: selectedCadence,
                          interval: 1
                        }
                      })
                    });
                    const { data: recData } = await parseJsonSafe(recResp);
                    if (!recResp.ok) {
                      logPlanClient('WARN', 'set_recurrence failed', { title: milestone.title, recData });
                      console.warn('Failed to set recurrence for', milestone.title, recData);
                    }
                  } catch (err) {
                    logPlanClient('ERROR', 'set_recurrence threw error', { title: milestone.title, err: err?.message || String(err) });
                    console.warn('Error setting recurrence for', milestone.title, err);
                  }
                }
                addLocalMessage(`✓ Added ${selectedCadence} reminders for all milestones.`, 'bot');
              } else if (wantsReminders) {
                addLocalMessage('Milestones created without recurring reminders.', 'bot');
              }

              if (exportWhere === 'ics' && exportWhen !== 'after review') {
                logPlanClient('INFO', 'Confirmed .ics export requested — individual milestones');
                await exportMilestonesIndividually(plan.milestones);
                addLocalMessage(`Confirmed. Downloading ${plan.milestones.length} calendar invite(s) — one per milestone.`, 'bot');
              } else if (exportWhere === 'ics' && exportWhen === 'after review') {
                addLocalMessage('Review complete. Use the button below when you are ready to export.', 'bot');
                showIcsExportButton('Export milestones to .ics when ready.', plan.milestones);
              } else {
                addLocalMessage(`Confirmed. Export target '${exportWhere}' selected. (Current automated file export supports .ics download.)`, 'bot');
                showIcsExportButton('If needed, you can still export these milestones as .ics.', plan.milestones);
              }
            } else {
              logPlanClient('ERROR', 'create_tasks failed', { taskData, taskText, status: resp.status });
              addLocalMessage('Failed to create tasks: ' + (taskData?.error || taskText || JSON.stringify(taskData)), 'bot');
            }
          } catch (err) {
            logPlanClient('ERROR', 'Network error while creating tasks', { err: err?.message || String(err) });
            addLocalMessage('Network error creating tasks: ' + err.message, 'bot');
          } finally {
            setFetching(false);
          }
        });
       });
    } else {
      logPlanClient('ERROR', 'Planning request failed', { status: res.status, data, rawText });
      addLocalMessage('Failed to generate plan: ' + (data?.error || rawText || JSON.stringify(data)), 'bot');
    }
  } catch (err) {
    logPlanClient('ERROR', 'Network error when generating plan', { err: err?.message || String(err) });
    addLocalMessage('Network error when generating plan: ' + err.message, 'bot');
  }
}

// wire quick shortcut: when bot asks "what would you like to accomplish?" show a small quick-prompt UI
function interceptGoalPrompt(text) {
  // called after adding a bot message; keep it tiny: show a "Start Project" suggestion that when clicked prompts user
  if (/what would you like to accomplish\?/i.test(text)) {
    const quick = document.createElement('div');
    quick.className = 'quick-actions';
    quick.innerHTML = `
      <p style="margin:4px 0;font-size:0.9em;color:var(--muted);">👇 Choose a planning shortcut</p>
      <button class="copy" id="startProjectBtn">Start Project</button>
      <button class="copy" id="studentPlansBtn">Student Lesson Plans</button>
    `;
    messages.appendChild(quick);
    document.getElementById('startProjectBtn').addEventListener('click', () => {
      const goal = prompt('Briefly describe the goal you want to accomplish (one sentence):');
      if (!goal) return;
      submitProjectGoal(goal);
      quick.remove();
    });
    document.getElementById('studentPlansBtn').addEventListener('click', async () => {
      const q = 'Create personalized lesson plans for all students';
      addLocalMessage(q, 'user');
      setFetching(true);
      showTyping();
      try {
        removeTyping();
        await submitPersonalizedLessonPlans(q);
      } finally {
        setFetching(false);
      }
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
