/* Front-End Checklist panel — vanilla JS */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const state = {
  categories: [],
  currentCategory: null,
  rules: [],
};

const ICONS = {
  accessibility: '♿', seo: '🔎', performance: '⚡', html: '🔤', css: '🎨',
  javascript: '📜', images: '🖼', security: '🛡', testing: '🧪', privacy: '🔒',
  internationalization: '🌐',
};

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function priorityClass(p) {
  const k = String(p || '').toLowerCase();
  return ['critical', 'high', 'medium', 'low'].includes(k) ? k : 'low';
}

function setMcpStatus(state, text) {
  const el = $('#mcpStatus');
  el.classList.remove('pending', 'ok', 'err');
  el.classList.add(state);
  el.textContent = text;
}

/* ============ Categories ============ */

async function loadCategories() {
  setMcpStatus('pending', '⏳ Đang kết nối MCP...');
  try {
    const res = await fetch('/api/fe-checklist/categories');
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    state.categories = (j.data?.categories || []).map(c => ({
      name: c.name,
      displayName: c.displayName || c.name,
      description: c.description || '',
      ruleCount: c.ruleCount || 0,
      icon: c.icon || c.name,
    }));
    renderCategories();
    setMcpStatus('ok', `✓ MCP online · ${state.categories.length} categories`);
  } catch (e) {
    setMcpStatus('err', '✗ MCP lỗi');
    $('#catList').innerHTML = `<li class="empty">Không kết nối được MCP: ${escapeHtml(e.message)}</li>`;
  }
}

function renderCategories() {
  const ul = $('#catList');
  if (!state.categories.length) {
    ul.innerHTML = '<li class="empty">Không có category.</li>';
    return;
  }
  ul.innerHTML = state.categories.map(c => `
    <li data-cat="${escapeHtml(c.name)}">
      <span>${ICONS[c.icon] || '📁'} ${escapeHtml(c.displayName)}</span>
      <span class="count">${c.ruleCount}</span>
    </li>
  `).join('');
  $$('#catList li[data-cat]').forEach(li => {
    li.addEventListener('click', () => loadRules(li.dataset.cat));
  });
}

/* ============ Rules ============ */

async function loadRules(cat) {
  state.currentCategory = cat;
  $$('#catList li').forEach(li => li.classList.toggle('active', li.dataset.cat === cat));
  const area = $('#rulesArea');
  area.innerHTML = '<p class="placeholder">⏳ Đang tải rules...</p>';
  try {
    const res = await fetch(`/api/fe-checklist/rules?category=${encodeURIComponent(cat)}`);
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    // Backend trả {category, count, rules: [...]}
    state.rules = (j.data && j.data.rules) || [];
    renderRules(cat, state.rules);
  } catch (e) {
    area.innerHTML = `<p class="placeholder">Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

function renderRules(cat, rules) {
  const area = $('#rulesArea');
  if (!rules.length) {
    area.innerHTML = '<p class="placeholder">Category này chưa có rules hoặc MCP trả format khác.</p>';
    return;
  }
  area.innerHTML = `
    <h2 style="margin:0 0 12px; color: var(--neon); text-transform: capitalize;">
      ${ICONS[cat] || '📁'} ${escapeHtml(cat)} <span style="color: var(--muted); font-size: 0.85em;">(${rules.length} rules)</span>
    </h2>
    <div class="rules-grid">
      ${rules.map(r => ruleCard(r)).join('')}
    </div>
  `;
  $$('.rule-card').forEach(card => {
    card.addEventListener('click', () => openRule(card.dataset.slug));
  });
}

function ruleCard(r) {
  const name = r.name || r.title || r.id || '(no name)';
  const slug = r.slug || r.id || '';
  const desc = r.description || r.summary || '';
  const prio = r.priority || r.severity || 'medium';
  return `
    <div class="rule-card" data-slug="${escapeHtml(slug)}">
      <div class="head">
        <div class="name">${escapeHtml(name)}</div>
        <span class="priority ${priorityClass(prio)}">${escapeHtml(prio)}</span>
      </div>
      <div class="slug">${escapeHtml(slug)}</div>
      <div class="desc">${escapeHtml(desc).substring(0, 180)}${desc.length > 180 ? '…' : ''}</div>
    </div>
  `;
}

/* ============ Modal rule detail ============ */

async function openRule(slug) {
  if (!slug) return;
  const modal = $('#ruleModal');
  const body = $('#modalBody');
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
  body.innerHTML = '<p>⏳ Đang tải...</p>';
  try {
    const res = await fetch(`/api/fe-checklist/rule/${encodeURIComponent(slug)}`);
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    renderRuleModal(j.data, slug);
  } catch (e) {
    body.innerHTML = `<p>Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

function renderRuleModal(d, slug) {
  const name = d.name || d.title || slug;
  const prio = d.priority || d.severity || 'medium';
  const cat = d.category || state.currentCategory || '';
  const desc = d.description || d.summary || '';
  const verify = d.verification || d.howToVerify || '';
  const fix = d.remediation || d.fix || '';
  const examples = d.examples || d.code || '';
  const refs = d.references || d.links || [];

  const sections = [];
  if (desc) sections.push(`<div class="modal-section"><h4>Mô tả</h4><div>${escapeHtml(desc)}</div></div>`);
  if (verify) sections.push(`<div class="modal-section"><h4>Cách kiểm tra</h4><div>${escapeHtml(verify)}</div></div>`);
  if (fix) sections.push(`<div class="modal-section"><h4>Cách sửa</h4><pre>${escapeHtml(fix)}</pre></div>`);
  if (examples) sections.push(`<div class="modal-section"><h4>Ví dụ</h4><pre>${escapeHtml(typeof examples === 'string' ? examples : JSON.stringify(examples, null, 2))}</pre></div>`);
  if (Array.isArray(refs) && refs.length) {
    sections.push(`<div class="modal-section"><h4>Tham khảo</h4><ul>${refs.map(r => `<li><a href="${escapeHtml(r.url || r.href || '#')}" target="_blank">${escapeHtml(r.title || r.url || r)}</a></li>`).join('')}</ul></div>`);
  }
  if (!sections.length) {
    sections.push(`<div class="modal-section"><pre>${escapeHtml(JSON.stringify(d, null, 2))}</pre></div>`);
  }

  $('#modalBody').innerHTML = `
    <h2>${escapeHtml(name)}</h2>
    <div class="modal-meta">
      <span class="priority ${priorityClass(prio)}">${escapeHtml(prio)}</span>
      <span>📂 ${escapeHtml(cat)}</span>
      <span>🔗 ${escapeHtml(slug)}</span>
    </div>
    ${sections.join('')}
  `;
}

$('#modalClose').addEventListener('click', closeModal);
$('#ruleModal').addEventListener('click', (e) => {
  if (e.target.id === 'ruleModal') closeModal();
});
function closeModal() {
  $('#ruleModal').classList.add('hidden');
  $('#ruleModal').setAttribute('aria-hidden', 'true');
}

/* ============ Tabs ============ */

$$('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    $$('.tab').forEach(b => b.classList.remove('active'));
    $$('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`#pane-${btn.dataset.tab}`).classList.add('active');
  });
});

/* ============ Search ============ */

$('#searchBtn').addEventListener('click', doSearch);
$('#searchInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

async function doSearch() {
  const q = $('#searchInput').value.trim();
  if (!q) return;
  const cat = state.currentCategory || '';
  const url = `/api/fe-checklist/search?q=${encodeURIComponent(q)}${cat ? `&category=${encodeURIComponent(cat)}` : ''}`;
  const area = $('#rulesArea');
  // Switch to rules tab
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === 'rules'));
  $$('.tab-pane').forEach(p => p.classList.toggle('active', p.id === 'pane-rules'));
  area.innerHTML = `<p class="placeholder">⏳ Tìm "${escapeHtml(q)}"...</p>`;
  try {
    const res = await fetch(url);
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    state.rules = j.rules || [];
    if (!state.rules.length) {
      area.innerHTML = `<p class="placeholder">Không tìm thấy rule nào khớp "${escapeHtml(q)}".</p>`;
      return;
    }
    renderRules('search', state.rules);
  } catch (e) {
    area.innerHTML = `<p class="placeholder">Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

/* ============ Workflow chips ============ */

$$('.chip[data-wf]').forEach(chip => {
  chip.addEventListener('click', async () => {
    const name = chip.dataset.wf;
    const area = $('#rulesArea');
    $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === 'rules'));
    $$('.tab-pane').forEach(p => p.classList.toggle('active', p.id === 'pane-rules'));
    area.innerHTML = `<p class="placeholder">⏳ Workflow "${escapeHtml(name)}"...</p>`;
    try {
      const res = await fetch(`/api/fe-checklist/workflow/${encodeURIComponent(name)}`);
      const j = await res.json();
      if (!j.ok) throw new Error(j.error);
      area.innerHTML = `
        <h2 style="margin:0 0 12px; color: var(--neon);">📋 Workflow: ${escapeHtml(name)}</h2>
        <div style="background: var(--panel); border:1px solid var(--border-glow); border-radius: 6px; padding: 18px;">
          <pre style="white-space: pre-wrap; color: var(--text-bright); margin: 0;">${escapeHtml(JSON.stringify(j.data, null, 2))}</pre>
        </div>
      `;
    } catch (e) {
      area.innerHTML = `<p class="placeholder">Lỗi: ${escapeHtml(e.message)}</p>`;
    }
  });
});

/* ============ review_code ============ */

$('#reviewBtn').addEventListener('click', async () => {
  const code = $('#reviewCode').value;
  const lang = $('#reviewLang').value;
  if (!code.trim()) {
    $('#reviewResult').textContent = '⚠ Paste code trước.';
    return;
  }
  const btn = $('#reviewBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Đang review...';
  $('#reviewResult').textContent = 'Đang gọi MCP review_code...';
  try {
    const res = await fetch('/api/fe-checklist/review-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, language: lang }),
    });
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    $('#reviewResult').textContent = JSON.stringify(j.data, null, 2);
  } catch (e) {
    $('#reviewResult').textContent = 'Lỗi: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ review_code';
  }
});

/* ============ audit_url ============ */

$('#auditBtn').addEventListener('click', async () => {
  const url = $('#auditUrl').value.trim();
  if (!url) {
    $('#auditResult').textContent = '⚠ Nhập URL.';
    return;
  }
  const btn = $('#auditBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Đang audit...';
  $('#auditResult').textContent = 'Đang gọi MCP audit_url...';
  try {
    const res = await fetch('/api/fe-checklist/audit-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    $('#auditResult').textContent = JSON.stringify(j.data, null, 2);
  } catch (e) {
    $('#auditResult').textContent = 'Lỗi: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ audit_url';
  }
});

/* ============ fix_rule ============ */

$('#fixBtn').addEventListener('click', async () => {
  const slug = $('#fixSlug').value.trim();
  const code = $('#fixCode').value;
  if (!slug) {
    $('#fixResult').textContent = '⚠ Nhập slug.';
    return;
  }
  const btn = $('#fixBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Đang sinh fix...';
  $('#fixResult').textContent = 'Đang gọi MCP fix_rule...';
  try {
    const res = await fetch('/api/fe-checklist/fix-rule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug, code }),
    });
    const j = await res.json();
    if (!j.ok) throw new Error(j.error);
    $('#fixResult').textContent = JSON.stringify(j.data, null, 2);
  } catch (e) {
    $('#fixResult').textContent = 'Lỗi: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ fix_rule';
  }
});

/* ============ Boot ============ */

loadCategories();
