/**
 * SkillMatch AI Agent Widget
 * Powered by the India Runs matching engine (Flask backend)
 * Features: typewriter effect, mini opportunity cards, suggested actions
 */

const BASE_URL = 'http://localhost:5000';

class SkillMatchAgent {
  constructor() {
    this.isOpen = false;
    this.profileId = localStorage.getItem('sm_profile_id');
    this.messageHistory = [];
    this.isTyping = false;
    this.init();
  }

  init() {
    this.injectHTML();
    this.bindEvents();
    // Auto-greet after 3 seconds
    setTimeout(() => this.greet(), 3000);
  }

  injectHTML() {
    document.body.insertAdjacentHTML('beforeend', `
      <!-- AI Agent FAB -->
      <button class="agent-fab" id="agent-fab" onclick="skillAgent.toggle()" aria-label="Open AI Assistant">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>
        <div class="fab-notif" id="agent-notif">1</div>
      </button>

      <!-- Agent Panel -->
      <div class="agent-panel" id="agent-panel">
        <div class="agent-header">
          <div class="agent-avatar-wrap">
            <div class="agent-avatar"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg></div>
            <div class="agent-online-dot"></div>
          </div>
          <div>
            <div class="agent-title">Opportunity Copilot</div>
            <div class="agent-subtitle">Multi-Signal Match Engine</div>
          </div>
          <button class="agent-close" onclick="skillAgent.toggle()">✕</button>
        </div>

        <div class="agent-messages" id="agent-messages"></div>

        <div class="agent-quick-actions" id="agent-quick-wrap">
          <div class="quick-actions-label">Quick Queries</div>
          <div class="quick-btns">
            <button class="qbtn" onclick="skillAgent.quickAsk('What should I apply to?')">Best Matches</button>
            <button class="qbtn" onclick="skillAgent.quickAsk('What skills am I missing?')">Skill Gaps</button>
            <button class="qbtn" onclick="skillAgent.quickAsk('Show me urgent deadlines')">Urgent</button>
            <button class="qbtn" onclick="skillAgent.quickAsk('Show me hackathons')">Hackathons</button>
          </div>
        </div>

        <div class="agent-input-area">
          <input class="agent-input" id="agent-input" type="text"
            placeholder="Query recommendations or missing skills..."
            onkeydown="if(event.key==='Enter') skillAgent.send()" />
          <button class="agent-send" onclick="skillAgent.send()" aria-label="Send">→</button>
        </div>
      </div>

      <!-- Confetti Canvas -->
      <canvas id="confetti-canvas"></canvas>

      <!-- Toast Tray -->
      <div class="toast-tray" id="toast-tray"></div>
    `);
  }

  bindEvents() {
    // Close on outside click
    document.addEventListener('click', (e) => {
      const panel = document.getElementById('agent-panel');
      const fab = document.getElementById('agent-fab');
      if (this.isOpen && !panel.contains(e.target) && !fab.contains(e.target)) {
        this.close();
      }
    });
  }

  toggle() {
    this.isOpen ? this.close() : this.open();
  }

  open() {
    this.isOpen = true;
    document.getElementById('agent-panel').classList.add('open');
    document.getElementById('agent-notif').style.display = 'none';
    document.getElementById('agent-input').focus();
  }

  close() {
    this.isOpen = false;
    document.getElementById('agent-panel').classList.remove('open');
  }

  greet() {
    if (this.messageHistory.length > 0) return;
    this.addBotMessage("Hello. I'm your **Opportunity Copilot**, integrated with your profile credentials and live listings.\n\nAsk me anytime to review top recommendations, detect skill gaps, or filter opportunities closing soon.", []);
  }

  quickAsk(question) {
    document.getElementById('agent-input').value = question;
    this.send();
    this.open();
  }

  addUserMessage(text) {
    const messages = document.getElementById('agent-messages');
    const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    messages.insertAdjacentHTML('beforeend', `
      <div class="msg-user fade-up">
        <div class="msg-bubble">${this.escapeHtml(text)}</div>
        <div class="msg-time">${time}</div>
      </div>`);
    this.scrollToBottom();
  }

  addTypingIndicator() {
    const messages = document.getElementById('agent-messages');
    messages.insertAdjacentHTML('beforeend', `
      <div class="msg-bot" id="typing-ind">
        <div class="msg-bubble" style="padding:10px 16px;">
          <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      </div>`);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    document.getElementById('typing-ind')?.remove();
  }

  addBotMessage(text, oppIds = []) {
    const messages = document.getElementById('agent-messages');
    const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    const msgId = 'msg-' + Date.now();

    messages.insertAdjacentHTML('beforeend', `
      <div class="msg-bot fade-up">
        <div class="msg-bubble" id="${msgId}"></div>
        <div class="msg-time">${time}</div>
        ${oppIds.length > 0 ? `<div id="${msgId}-cards"></div>` : ''}
      </div>`);

    // Typewriter effect
    this.typewriter(msgId, this.formatMarkdown(text), () => {
      if (oppIds.length > 0) {
        this.renderMiniCards(msgId + '-cards', oppIds);
      }
    });

    this.scrollToBottom();
  }

  typewriter(elementId, html, onDone) {
    const el = document.getElementById(elementId);
    if (!el) return;
    // Extract text and render progressively
    const words = html.split(' ');
    let i = 0;
    el.innerHTML = '';
    const interval = setInterval(() => {
      if (i < words.length) {
        el.innerHTML += (i === 0 ? '' : ' ') + words[i];
        i++;
        this.scrollToBottom();
      } else {
        clearInterval(interval);
        if (onDone) onDone();
      }
    }, 25); // Fast typewriter
  }

  renderMiniCards(containerId, oppIds) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Fetch opportunity details from backend
    fetch(`${BASE_URL}/api/opportunities?profile_id=${this.profileId}`)
      .then(r => r.json())
      .then(opps => {
        const matched = opps.filter(o => oppIds.includes(o.id)).slice(0, 3);
        matched.forEach(opp => {
          const card = document.createElement('div');
          card.className = 'chat-opp-card';
          card.onclick = () => window.location.href = `/opportunity.html?id=${opp.id}`;
          card.innerHTML = `
            <div style="width:28px;height:28px;border-radius:6px;background:${opp.orgColor};display:flex;align-items:center;justify-content:center;font-size:0.65rem;font-weight:800;color:white;flex-shrink:0;">${opp.orgInitials}</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.8rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${opp.title}</div>
              <div style="font-size:0.72rem;color:var(--text-muted);">${opp.org}</div>
            </div>
            <div class="chat-opp-pct">${opp.match?.percentage ?? '--'}%</div>
          `;
          container.appendChild(card);
        });
      })
      .catch(() => {});
  }

  formatMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  scrollToBottom() {
    const messages = document.getElementById('agent-messages');
    messages.scrollTop = messages.scrollHeight;
  }

  async send() {
    if (this.isTyping) return;
    const input = document.getElementById('agent-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    this.addUserMessage(message);
    this.isTyping = true;
    this.addTypingIndicator();

    try {
      const res = await fetch(`${BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, profile_id: this.profileId })
      });
      const data = await res.json();
      this.removeTypingIndicator();
      this.addBotMessage(data.response, data.oppIds || []);
    } catch (err) {
      this.removeTypingIndicator();
      this.addBotMessage('⚠️ Connection error. Make sure the backend is running at localhost:5000.', []);
    }

    this.isTyping = false;
    this.messageHistory.push(message);
  }
}

// ── Confetti Engine ────────────────────────────────────────────
function fireConfetti() {
  const canvas = document.getElementById('confetti-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.display = 'block';

  const pieces = [];
  const colors = ['#2563eb','#3b82f6','#60a5fa','#059669','#34d399','#f59e0b','#fbbf24'];

  for (let i = 0; i < 120; i++) {
    pieces.push({
      x: Math.random() * canvas.width,
      y: Math.random() * -canvas.height * 0.5,
      vx: (Math.random() - 0.5) * 6,
      vy: Math.random() * 4 + 2,
      rotation: Math.random() * 360,
      rotationSpeed: (Math.random() - 0.5) * 8,
      size: Math.random() * 10 + 5,
      color: colors[Math.floor(Math.random() * colors.length)],
      shape: Math.random() > 0.5 ? 'rect' : 'circle'
    });
  }

  let frame = 0;
  const MAX_FRAMES = 150;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.1;
      p.rotation += p.rotationSpeed;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rotation * Math.PI) / 180);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, 1 - frame / MAX_FRAMES);
      if (p.shape === 'rect') {
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    });

    frame++;
    if (frame < MAX_FRAMES) requestAnimationFrame(draw);
    else { canvas.style.display = 'none'; ctx.clearRect(0,0,canvas.width,canvas.height); }
  }

  requestAnimationFrame(draw);
}

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const tray = document.getElementById('toast-tray');
  if (!tray) return;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type] || '✅'}</span><span>${msg}</span>`;
  tray.appendChild(t);
  setTimeout(() => {
    t.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => t.remove(), 300);
  }, 3500);
}

// ── Apply success modal ───────────────────────────────────────
function showApplySuccess(oppTitle) {
  const overlay = document.createElement('div');
  overlay.className = 'apply-modal-overlay';
  overlay.innerHTML = `
    <div class="apply-modal">
      <div class="big-check">🎉</div>
      <h3>Application Recorded!</h3>
      <p style="margin-top:8px;">Your application for <strong>${oppTitle}</strong> has been saved to the database.</p>
      <p style="margin-top:6px;font-size:0.8rem;color:var(--text-subtle);">Track your status in My Applications →</p>
      <div style="margin-top:24px;display:flex;gap:10px;justify-content:center;">
        <a href="/bookmarks.html" class="btn btn-primary">View My Applications</a>
        <button class="btn btn-secondary" onclick="this.closest('.apply-modal-overlay').remove()">Continue Browsing</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
}

// ── API helpers ───────────────────────────────────────────────
async function apiGet(path) {
  const r = await fetch(BASE_URL + path);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(BASE_URL + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return r.json();
}

async function apiDelete(path, body) {
  const r = await fetch(BASE_URL + path, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return r.json();
}

// ── Countdown timer ───────────────────────────────────────────
function startCountdown(el, deadlineStr) {
  function update() {
    const diff = new Date(deadlineStr) - new Date();
    if (diff <= 0) { el.textContent = 'CLOSED'; return; }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    if (h < 24) {
      el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    }
  }
  update();
  setInterval(update, 1000);
}

// ── Profile ID helpers ────────────────────────────────────────
function getProfileId() { return localStorage.getItem('sm_profile_id'); }
function setProfileId(id) { localStorage.setItem('sm_profile_id', id); }
function requireLogin(redirect = '/') {
  const id = getProfileId();
  if (!id) { window.location.href = redirect; return null; }
  return id;
}
