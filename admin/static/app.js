/* =====================================================================
 * 3105 Repo Builder - Frontend logic
 * ===================================================================== */

const state = {
  repositories: [],
  currentRepo: null,
  repoMeta: {},
  packages: [],
  packagesMeta: [],
  sharedScreens: [],
  sharedOS: [],
  assets: [],
  packageFiles: [],
  editingIndex: null,
  // Search & pagination
  pkgSearchQuery: '',
  pkgPage: 1,
  pkgPageSize: 5,
  // Blog pagination
  blogPage: 1,
  blogPageSize: 5,
  blogPosts: [
    { icon: '📦', title: 'Cách cài đặt Repository trên ứng dụng 3105', date: '2 ngày trước' },
    { icon: '🛡️', title: 'Bảo mật khi sử dụng Mod - Những lưu ý quan trọng', date: '5 ngày trước' },
    { icon: '⚡', title: 'Cập nhật v1.2 - Tính năng mới & cải tiến', date: '1 tuần trước' },
    { icon: '🎨', title: 'Hướng dẫn tạo Custom Dialer cho riêng bạn', date: '2 tuần trước' },
    { icon: '🎮', title: 'So sánh các gói Custom: VNG vs Global vs KR', date: '3 tuần trước' },
    { icon: '🔧', title: 'Khắc phục lỗi thường gặp khi cập nhật Repository', date: '1 tháng trước' },
    { icon: '💎', title: 'Premium Features có gì mới trong bản cập nhật', date: '1 tháng trước' },
    { icon: '🔧', title: 'Sửa lỗi thường gặp khi sử dụng 3105', date: '1 tháng trước' },
    { icon: '🚀', title: 'Tối ưu hiệu suất thiết bị với các mẹo nhỏ', date: '1 tháng trước' },
    { icon: '📱', title: 'Hỗ trợ iOS 17 - Danh sách tính năng tương thích', date: '2 tháng trước' },
  ],
  // Theo dõi thay đổi để sinh commit message
  changes: {
    added: [],    // [{identifier, name}]
    edited: [],   // [{identifier, name}]
    deleted: [],  // [{identifier, name}]
  },
};

// ---------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return Array.from(document.querySelectorAll(sel)); }

function toast(msg, type = 'info') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'fixed bottom-5 right-5 px-4 py-2 rounded-lg shadow-lg text-sm z-50 text-white';
  el.classList.add(type === 'error' ? 'bg-red-600' : type === 'success' ? 'bg-emerald-600' : 'bg-slate-900');
  el.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add('hidden'), 3500);
}

// ============================================================
// PUSH PROGRESS MODAL - Hiển thị 4 bước git với kết quả chi tiết
// ============================================================
function showPushProgressModal(steps) {
  // Xoá modal cũ nếu có
  const old = document.getElementById('pushProgressModal');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'pushProgressModal';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;';

  const html = steps.map(s => `
    <div id="step-${s.id}" style="display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:rgba(255,255,255,0.05);border-radius:6px;margin-bottom:6px;border:1px solid rgba(255,255,255,0.08);">
      <div id="step-${s.id}-icon" style="font-size:18px;line-height:1;flex-shrink:0;width:24px;text-align:center;color:#888;">◯</div>
      <div style="flex:1;min-width:0;">
        <div style="font-family:'Press Start 2P',monospace;font-size:11px;color:#fff;font-weight:700;">${s.label}</div>
        <div id="step-${s.id}-detail" style="font-family:monospace;font-size:10px;color:#888;margin-top:4px;max-height:60px;overflow:auto;white-space:pre-wrap;word-break:break-all;display:none;"></div>
      </div>
    </div>
  `).join('');

  overlay.innerHTML = `
    <div style="background:#0f1626;border:1px solid #39ff14;border-radius:10px;padding:20px;max-width:520px;width:90%;box-shadow:0 8px 32px rgba(57,255,20,0.2);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div style="font-family:'Press Start 2P',monospace;font-size:13px;color:#39ff14;">🚀 ĐANG PUSH</div>
        <button id="pushProgressClose" style="background:none;border:none;color:#888;font-size:18px;cursor:pointer;">✕</button>
      </div>
      <div id="pushProgressSteps">${html}</div>
      <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
        <button id="pushProgressDismiss" class="btn neon-delete" style="display:none;">Đóng</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  document.getElementById('pushProgressClose').onclick = () => dismissProgressModal();
  document.getElementById('pushProgressDismiss').onclick = () => dismissProgressModal();
}

function setStepStatus(stepId, status, detail) {
  const iconEl = document.getElementById('step-' + stepId + '-icon');
  const detailEl = document.getElementById('step-' + stepId + '-detail');
  if (!iconEl) return;

  const icons = { running: '⏳', done: '✅', skipped: '⏭', error: '❌', pending: '◯' };
  const colors = { running: '#39ff14', done: '#39ff14', skipped: '#888', error: '#ff006e', pending: '#888' };

  iconEl.textContent = icons[status] || '◯';
  iconEl.style.color = colors[status] || '#888';

  if (detail && status !== 'pending') {
    detailEl.textContent = detail;
    detailEl.style.display = 'block';
    detailEl.style.color = status === 'error' ? '#ff006e' : '#aaa';
  } else {
    detailEl.style.display = 'none';
  }

  // Khi tất cả steps xong → hiện nút Đóng
  if (status === 'done' || status === 'error' || status === 'skipped') {
    const allSteps = ['save', 'pull', 'add', 'status', 'commit', 'push'];
    const allDone = allSteps.every(s => {
      const el = document.getElementById('step-' + s + '-icon');
      if (!el) return false;
      return ['✅', '❌', '⏭'].some(i => el.textContent.indexOf(i) !== -1);
    });
    if (allDone) {
      const dismiss = document.getElementById('pushProgressDismiss');
      if (dismiss) dismiss.style.display = 'inline-block';
    }
  }
}

function dismissProgressModal() {
  const m = document.getElementById('pushProgressModal');
  if (m) m.remove();
}

async function api(path, options = {}) {
  // Không set Content-Type khi dùng FormData (upload), browser tự điền boundary
  const isFormData = options.body instanceof FormData;
  const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
  const res = await fetch(path, {
    headers,
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.description || data.message || `HTTP ${res.status}`);
  }
  return data;
}

// replaceAll không có sẵn ở một số trình duyệt cũ — dùng replace + regex /g.
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeReg(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return '0 B';
  bytes = Number(bytes);
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(bytes >= 100 ? 0 : 1)} ${units[i]}`;
}

// SHA-256 hex 64 ký tự, in hoa
function normalizeSha256(s) {
  return String(s || '').trim().toUpperCase();
}

// ---------------------------------------------------------------------
// Identifier helpers
// ---------------------------------------------------------------------
//
// Quy ước: package identifier dạng "owen-XXX" với XXX là số 3 chữ số
// (padding tự động). Hàm này tìm các số trống trong dãy hiện tại.

function findMissingIdentifierIndices() {
  const used = new Set();
  state.packages.forEach(p => {
    const m = /^owen-(\d+)$/.exec(p.identifier || '');
    if (m) used.add(parseInt(m[1], 10));
  });
  // Tìm các số trống trong khoảng [0, maxUsed]
  const missing = [];
  if (used.size === 0) {
    return [0];
  }
  const max = Math.max(...used);
  for (let i = 0; i <= max; i++) {
    if (!used.has(i)) missing.push(i);
  }
  // Nếu không có trống nào → gợi �ý số tiếp theo
  if (missing.length === 0) missing.push(max + 1);
  return missing;
}

function buildMissingIdentifierHint() {
  const missing = findMissingIdentifierIndices();
  if (missing.length === 0) return 'owen-001';
  const padded = missing.map(n => `owen-${String(n).padStart(3, '0')}`);
  if (padded.length <= 6) return padded.join(', ');
  return padded.slice(0, 6).join(', ') + ` … (+${padded.length - 6} nữa)`;
}



async function loadRepositories() {
  try {
    const data = await api('/api/repositories');
    state.repositories = data.repositories || [];
    const sel = $('#repoSelect');
    sel.innerHTML = '';
    if (state.repositories.length === 0) {
      sel.innerHTML = '<option value="">— không có repo —</option>';
      toast('Chưa có repo nào dưới thư mục repositories/.', 'error');
      return;
    }
    state.repositories.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      sel.appendChild(opt);
    });
    if (state.repositories.includes('demo')) {
      sel.value = 'demo';
    } else {
      sel.value = state.repositories[0];
    }
    state.currentRepo = sel.value;
    await loadRepo();
  } catch (err) {
    toast(`Lỗi: ${err.message}`, 'error');
  }
}

async function loadRepo() {
  const repo = state.currentRepo;
  if (!repo) return;

  // Reset search & pagination khi chuyển repo
  state.pkgPage = 1;
  state.pkgSearchQuery = '';
  $('#pkgSearchInput').value = '';

  try {
    // Load packages + meta
    const data = await api(`/api/repo/${repo}/packages`);
    state.repoMeta = data.repoMeta || {};
    state.sharedScreens = data.sharedScreens || (window.DEFAULT_SCREENSHOTS || []);
    state.sharedOS = data.sharedOS || (window.DEFAULT_OS_RULES || []);
    // packagesMeta đi kèm từ backend — dùng để ghi lại YAML đúng anchor
    state.packagesMeta = Array.isArray(data.packagesMeta) ? data.packagesMeta : [];
    state.packages = (data.packages || []).map(normalizePackage);

    // Load file listings
    const files = await api(`/api/repo/${repo}/files`);
    state.assets = files.assets || [];
    state.packageFiles = (files.packages || []).map(p => p.replace(/^packages\//, ''));

    renderMeta();
    renderPackageList();
    // Reset tracking changes cho session mới
    state.changes = { added: [], edited: [], deleted: [] };
    updateAvatar();
    toast(`Đã tải ${state.packages.length} package từ repo "${repo}".`, 'success');
  } catch (err) {
    toast(`Lỗi tải repo: ${err.message}`, 'error');
  }
}

function updateAvatar() {
  const el = $('#mast-avatar');
  if (!el) return;
  const iconPath = state.repoMeta.icon;
  if (iconPath) {
    const repo = state.currentRepo;
    el.innerHTML = `<img src="/repo-asset?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(iconPath)}" alt="repo icon" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none';this.nextElementSibling&&(this.nextElementSibling.style.display='')"/>` +
      `<svg viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg" style="display:none;position:absolute;inset:0;width:100%;height:100%;">` +
      `<rect x="0" y="0" width="52" height="52" rx="4" fill="rgba(10,14,26,0.95)"/>` +
      `<text x="26" y="34" text-anchor="middle" font-family="'Press Start 2P',monospace" font-size="12" fill="#39ff14">?</text>` +
      `</svg>`;
  } else {
    el.innerHTML = `<svg viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%;height:100%;">` +
      `<defs><linearGradient id="avg" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#39ff14"/><stop offset="100%" stop-color="#00f0ff"/></linearGradient></defs>` +
      `<rect x="0" y="0" width="52" height="52" rx="4" fill="rgba(10,14,26,0.95)" stroke="url(#avg)" stroke-width="1.5"/>` +
      `<text x="26" y="34" text-anchor="middle" font-family="'Press Start 2P',monospace" font-size="12" fill="url(#avg)" filter="url(#glow)">?</text>` +
      `<filter id="glow"><feGaussianBlur stdDeviation="0.8"/></filter>` +
      `<rect x="16" y="20" width="3" height="3" fill="#39ff14" opacity="0.7"/>` +
      `<rect x="33" y="20" width="3" height="3" fill="#39ff14" opacity="0.7"/>` +
      `</svg>`;
  }
}

function normalizePackage(pkg, idx) {
  // Giữ nguyên cờ anchor từ backend; chỉ thêm default nếu backend không cung cấp.
  const meta = state.packagesMeta[idx] || {};
  return {
    ...pkg,
    __use_default_os: !!meta.use_anchor_os,
    __use_default_screens: !!meta.use_anchor_screens,
  };
}

// ---------------------------------------------------------------------
// Render: repo meta
// ---------------------------------------------------------------------

function renderMeta() {
  $('#meta_identifier').value = state.repoMeta.identifier || '';
  $('#meta_name').value = state.repoMeta.name || '';
  $('#meta_description').value = state.repoMeta.description || '';
  $('#meta_accentColor').value = state.repoMeta.accentColor || '#FF3B30';
  updateAvatar();

  const iconSel = $('#meta_icon');
  iconSel.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— chọn ảnh —';
  iconSel.appendChild(placeholder);
  state.assets.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    iconSel.appendChild(opt);
  });
  // Đảm bảo icon hiện tại được chọn dù có/không có trong danh sách scan
  if (state.repoMeta.icon) {
    const exists = Array.from(iconSel.options).some(o => o.value === state.repoMeta.icon);
    if (!exists) {
      const opt = document.createElement('option');
      opt.value = state.repoMeta.icon;
      opt.textContent = `${state.repoMeta.icon} (không tìm thấy)`;
      iconSel.appendChild(opt);
    }
    iconSel.value = state.repoMeta.icon;
  }
}

// ---------------------------------------------------------------------
// Render: blog list (with pagination)
// ---------------------------------------------------------------------
function renderBlogList() {
  const list = $('#blogList');
  if (!list) return;

  const totalPosts = state.blogPosts.length;
  const totalPages = Math.max(1, Math.ceil(totalPosts / state.blogPageSize));
  if (state.blogPage > totalPages) state.blogPage = totalPages;

  const start = (state.blogPage - 1) * state.blogPageSize;
  const pageItems = state.blogPosts.slice(start, start + state.blogPageSize);

  $('#blogCount').textContent = `${totalPosts} bài viết`;

  list.innerHTML = pageItems.map(post => `
    <div class="blog-item">
      <span class="blog-icon">${post.icon}</span>
      <a href="#" class="blog-link">${post.title}</a>
      <span class="blog-date">${post.date}</span>
    </div>
  `).join('');

  const paginationEl = $('#blogPagination');
  const pageNumbers = $('#blogPageNumbers');
  const btnPrev = $('#blogPagePrev');
  const btnNext = $('#blogPageNext');

  if (totalPosts <= state.blogPageSize) {
    paginationEl?.classList.add('hidden');
  } else {
    paginationEl?.classList.remove('hidden');
    btnPrev.disabled = state.blogPage <= 1;
    btnNext.disabled = state.blogPage >= totalPages;

    const half = Math.floor(MAX_PAGE_BUTTONS / 2);
    let startPage = Math.max(1, state.blogPage - half);
    let endPage = Math.min(totalPages, startPage + MAX_PAGE_BUTTONS - 1);
    if (endPage - startPage < MAX_PAGE_BUTTONS - 1) {
      startPage = Math.max(1, endPage - MAX_PAGE_BUTTONS + 1);
    }
    pageNumbers.innerHTML = '';
    for (let p = startPage; p <= endPage; p++) {
      const btn = document.createElement('button');
      btn.textContent = p;
      btn.className = `page-num ${p === state.blogPage ? 'active' : ''}`;
      btn.addEventListener('click', () => {
        state.blogPage = p;
        renderBlogList();
      });
      pageNumbers.appendChild(btn);
    }
  }
}

// ---------------------------------------------------------------------
// Render: package list (with search filter + pagination)
// ---------------------------------------------------------------------
const MAX_PAGE_BUTTONS = 5;

function renderPackageList() {
  const list = $('#packageList');
  const q = state.pkgSearchQuery.toLowerCase().trim();

  // Lọc
  const filtered = q
    ? state.packages.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.identifier || '').toLowerCase().includes(q) ||
        (p.version || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) ||
        (p.author || '').toLowerCase().includes(q)
      )
    : state.packages;

  // Reset page nếu vượt quá
  const totalPages = Math.max(1, Math.ceil(filtered.length / state.pkgPageSize));
  if (state.pkgPage > totalPages) state.pkgPage = totalPages;

  // Slice trang hiện tại
  const start = (state.pkgPage - 1) * state.pkgPageSize;
  const pageItems = filtered.slice(start, start + state.pkgPageSize);

  // Count / pagination UI
  $('#packageCount').textContent = `${filtered.length} / ${state.packages.length} package`;
  $('#emptyHint').classList.toggle('hidden', filtered.length > 0);
  $('#packageList').style.display = filtered.length === 0 ? 'none' : 'block';

  const paginationEl = $('#pkgPagination');
  const paginationInfo = $('#pkgPaginationInfo');
  const pageNumbers = $('#pkgPageNumbers');
  const btnPrev = $('#pkgPagePrev');
  const btnNext = $('#pkgPageNext');

  if (filtered.length <= state.pkgPageSize) {
    paginationEl?.classList.add('hidden');
  } else {
    paginationEl?.classList.remove('hidden');
    paginationInfo.textContent = `Hiển thị ${start + 1}–${Math.min(start + pageItems.length, filtered.length)} của ${filtered.length}`;

    // Prev / Next
    btnPrev.disabled = state.pkgPage <= 1;
    btnNext.disabled = state.pkgPage >= totalPages;

    // Page number buttons (slide window)
    const half = Math.floor(MAX_PAGE_BUTTONS / 2);
    let startPage = Math.max(1, state.pkgPage - half);
    let endPage = Math.min(totalPages, startPage + MAX_PAGE_BUTTONS - 1);
    if (endPage - startPage < MAX_PAGE_BUTTONS - 1) {
      startPage = Math.max(1, endPage - MAX_PAGE_BUTTONS + 1);
    }
    pageNumbers.innerHTML = '';
    for (let p = startPage; p <= endPage; p++) {
      const btn = document.createElement('button');
      btn.textContent = p;
      btn.className = `page-num ${p === state.pkgPage ? 'active' : ''}`;
      btn.addEventListener('click', () => {
        state.pkgPage = p;
        renderPackageList();
      });
      pageNumbers.appendChild(btn);
    }
  }

  // Render rows
  list.innerHTML = '';
  pageItems.forEach((pkg, i) => {
    const realIdx = state.packages.indexOf(pkg);
    const row = document.createElement('div');
    row.className = 'pkg-item';
    row.innerHTML = `
      <div class="flex-shrink-0 w-9 h-9 rounded-md bg-slate-200 overflow-hidden flex items-center justify-center">
        ${pkg.icon
          ? `<img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(pkg.icon)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none'" />`
          : '<span class="text-slate-400 text-[10px]">no img</span>'}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="font-medium text-sm truncate">${escapeHtml(pkg.name || '(chưa có tên)')}</span>
          ${pkg.featured ? '<span class="bg-yellow-100 text-yellow-800 text-[10px] px-1.5 py-0.5 rounded-full">featured</span>' : ''}
          ${pkg.isPrivate ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full" style="background:transparent;border:none;color:#39ff14;text-shadow:0 0 4px rgba(57,255,20,0.7);">private</span>' : ''}
          ${pkg.kind ? `<span class="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.5 rounded-full">${escapeHtml(pkg.kind)}</span>` : ''}
        </div>
        <div class="text-[11px] text-slate-500 truncate">
          <code>${escapeHtml(pkg.identifier)}</code> · v${escapeHtml(pkg.version || '?')} · ${escapeHtml(pkg.category || '—')}
        </div>
      </div>
      <div class="hidden sm:block text-[11px] text-slate-500 text-right flex-shrink-0">
        <div>${formatSize(pkg.size)}</div>
        <div class="truncate max-w-[100px]" title="${escapeHtml(pkg.sha256 || '')}">${escapeHtml((pkg.sha256 || '').slice(0, 10))}…</div>
      </div>
      <div class="flex gap-1 flex-shrink-0">
        <button data-action="edit" data-idx="${realIdx}" class="btn btn-xs neon-edit whitespace-nowrap">Sửa</button>
        <button data-action="duplicate" data-idx="${realIdx}" class="hidden sm:table-cell btn btn-xs neon-edit" title="Sao chép">Copy</button>
        <button data-action="delete" data-idx="${realIdx}" class="btn btn-xs neon-delete">✕</button>
      </div>
    `;
    list.appendChild(row);
  });

  $$('#packageList [data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx, 10);
      const action = btn.dataset.action;
      if (action === 'edit') openModal(idx);
      else if (action === 'delete') deletePackage(idx);
      else if (action === 'duplicate') duplicatePackage(idx);
    });
  });
}

// ---------------------------------------------------------------------
// Modal: thêm / sửa package
// ---------------------------------------------------------------------

// Định nghĩa global để openModal() gọi được (không phụ thuộc bindFormEvents)
function syncDlClearBtn() {
  const dlInput = $('#f_download');
  const dlClear = $('#f_download_clear');
  if (!dlClear || !dlInput) return;
  dlClear.classList.toggle('hidden', !dlInput.value);
}

function openModal(editIdx = null) {
  state.editingIndex = editIdx;
  const isEdit = editIdx !== null;

  // Tính số Identifier trống để gợi ý (chỉ khi THÊM mới)
  let hintHtml = '';
  if (!isEdit) {
    const hint = buildMissingIdentifierHint();
    hintHtml = `
      <div class="bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-md px-3 py-2 mb-3">
        💡 <b>Identifier trống đang có sẵn:</b> <code class="bg-amber-100 px-1 rounded">${escapeHtml(hint)}</code>
        <span class="text-amber-700">— tool sẽ tự lấy số trống đầu tiên. Có thể sửa tay nếu muốn.</span>
      </div>`;
  }

  $('#modalTitle').textContent = isEdit ? `Sửa package #${editIdx + 1}` : 'Thêm package mới';
  $('#modalStatus').textContent = isEdit
    ? `Đang sửa: ${state.packages[editIdx].identifier || '(chưa có id)'}`
    : 'Điền thông tin bên dưới, sau đó bấm Lưu package.';

  const pkg = isEdit
    ? { ...state.packages[editIdx] }
    : newPackageTemplate();

  $('#modalBody').innerHTML = hintHtml + buildFormHtml(pkg);
  bindFormEvents();
  // Pre-fill file .3105 đã chọn — combobox input chỉ hiện TÊN FILE (vd: myapp.3105), không kèm "packages/"
  const dlInput = $('#f_download');
  if (dlInput && pkg.download) {
    const fileName = String(pkg.download).replace(/^packages\//, '').replace(/^.*[\\\/]/, '');
    dlInput.value = fileName;
    syncDlClearBtn();
  }
  $('#modal').classList.remove('hidden');
  $('#modal').classList.add('flex');
}

function closeModal() {
  $('#modal').classList.add('hidden');
  $('#modal').classList.remove('flex');
  state.editingIndex = null;
}

function newPackageTemplate() {
  // Ưu tiên dùng số Identifier trống trong dãy owen-XXX
  const missing = findMissingIdentifierIndices();
  const nextNum = missing[0];
  const id = `owen-${String(nextNum).padStart(3, '0')}`;
  return {
    identifier: id,
    name: '',
    author: '@owenindahouse',
    version: '1.0.0',
    summary: '',
    category: 'Customization',
    tags: ['CUSTOM'],
    icon: '',
    banner: '',
    screenshots: [],
    download: '',
    sha256: '',
    size: 0,
    password: '',
    featured: false,
    isPrivate: false,
    description: '',
    changelog: '🎉 v1.0.0 — Phát hành lần đầu',
    __use_default_os: true,
    __use_default_screens: true,
  };
}

function buildFormHtml(pkg) {
  // Nếu chưa có os_minimum/os_maximum mà có supportedOS (custom), fill vào
  if ((!pkg.os_minimum || !pkg.os_maximum) && Array.isArray(pkg.supportedOS) && pkg.supportedOS[0]) {
    if (!pkg.os_minimum) pkg.os_minimum = String(pkg.supportedOS[0].minimum || '');
    if (!pkg.os_maximum) pkg.os_maximum = String(pkg.supportedOS[0].maximum || '');
  }
  const options = (items, selected) => items.map(it =>
    `<option value="${escapeHtml(it)}" ${it === selected ? 'selected' : ''}>${escapeHtml(it)}</option>`
  ).join('');

  const assetOptions = (current) => {
    const opts = ['<option value="">— chọn ảnh —</option>'];
    state.assets.forEach(p => {
      const sel = p === current ? 'selected' : '';
      opts.push(`<option value="${escapeHtml(p)}" ${sel}>${escapeHtml(p)}</option>`);
    });
    if (current && !state.assets.includes(current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)} (không tìm thấy)</option>`);
    }
    return opts.join('');
  };

  const packageOptions = (current) => {
    // Trả về giá trị để set vào input (combobox), không phải <option>
    return escapeHtml(current || '');
  };

  const defaultScreens = window.DEFAULT_SCREENSHOTS || [];

  return `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">File .3105 (chọn để tự động điền SHA-256 + size)</span>
        <div class="flex gap-2 mt-1">
          <div class="flex-1 relative">
            <input id="f_download" type="text" autocomplete="off" placeholder="— gõ để tìm file .3105 —"
                   class="w-full border border-slate-300 rounded-md px-3 py-1.5 text-sm pr-8" />
            <button type="button" id="f_download_clear" title="Xoá lựa chọn"
                    class="absolute right-1 top-1/2 -translate-y-1/2 hidden w-6 h-6 text-slate-400 hover:text-slate-600 text-base leading-none">✕</button>
            <div id="f_download_menu" class="hidden absolute z-50 left-0 right-0 mt-1 max-h-60 overflow-y-auto bg-white border border-slate-300 rounded-md shadow-lg text-sm"></div>
          </div>
          <button id="btnAutoFill" type="button" class="btn btn-sm neon-edit whitespace-nowrap">⚡ Lấy hash</button>
          <button id="btnDeletePackageFile" type="button" class="btn btn-sm neon-delete" title="Xoá file .3105 đã chọn"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg></button>
        </div>
        <div id="pkgUploadZone" class="mt-2 border-2 border-dashed border-slate-300 rounded-md p-3 text-center text-xs text-slate-500 cursor-pointer hover:border-slate-400">
          📂 Kéo thả file <code>.3105</code> vào đây, hoặc bấm để chọn file → file sẽ tự upload vào <code>packages/</code>
          <input type="file" id="f_pkg_upload" accept=".3105,.3105pass,.tendies" multiple class="hidden" />
        </div>
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Identifier *</span>
        <input id="f_identifier" value="${escapeHtml(pkg.identifier)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tên hiển thị *</span>
        <input id="f_name" value="${escapeHtml(pkg.name)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Phiên bản *</span>
        <input id="f_version" value="${escapeHtml(pkg.version)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tác giả *</span>
        <input id="f_author" value="${escapeHtml(pkg.author)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Tóm tắt (summary) *</span>
        <input id="f_summary" value="${escapeHtml(pkg.summary)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Category *</span>
        <select id="f_category" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">
          ${options(window.CATEGORIES || [], pkg.category)}
        </select>
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tags (phân cách bằng dấu phẩy)</span>
        <input id="f_tags" value="${escapeHtml((pkg.tags || []).join(', '))}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Kind (để trống = package thường)</span>
        <input id="f_kind" value="${escapeHtml(pkg.kind || '')}" placeholder="vd: wallpaper" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <div class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_no_publishedAt" class="accent-red-500" />
          <label for="f_no_publishedAt" class="cursor-pointer">Không dùng publishedAt</label>
        </span>
        <div id="publishedAtBox" class="flex items-center gap-2 mt-1">
          <input id="f_publishedAt" type="datetime-local" step="1" class="flex-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
          <button type="button" id="btnNowPublishedAt" class="btn btn-xs neon-edit whitespace-nowrap">🕐 Bây giờ</button>
        </div>
      </div>

      <div class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <span>Icon (ảnh đại diện package)</span>
          <span class="text-slate-400" id="iconPickerCurrent"></span>
        </span>
        <div class="flex flex-wrap items-center gap-2 mb-2 mt-1">
          <span class="text-xs text-slate-500">Thư mục ảnh:</span>
          <select id="f_icon_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 min-w-0">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnIconRefreshFolders" class="btn btn-xs neon-edit">↻</button>
          <button type="button" id="btnDeleteIconFolder" class="btn btn-xs neon-delete" title="Xoá thư mục hiện tại"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg></button>
          <div class="relative" id="iconAddDropdown">
            <button type="button" id="btnIconAdd" class="btn btn-xs neon-edit">+</button>
            <div id="iconAddMenu" class="hidden absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg z-10 min-w-[140px]">
              <button type="button" id="btnIconNewFolder" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-t-md">📁 Thêm thư mục</button>
              <button type="button" id="btnIconUpload" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-b-md">⬆ Upload ảnh</button>
            </div>
          </div>
          <input type="file" id="f_icon_upload" accept="image/*" multiple class="hidden" />
          <input type="search" id="f_icon_search" placeholder="🔍 tìm ảnh..." class="text-xs px-2 py-1 rounded border border-slate-300" />
          <button type="button" id="btnIconToggle" class="btn btn-xs neon-edit ml-auto">Hiện ảnh</button>
        </div>
        <div id="iconPickerGrid" class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 hidden"></div>
        <input type="hidden" id="f_icon" value="${escapeHtml(pkg.icon || '')}" />
        <p class="text-xs text-slate-400 mt-1">Bấm vào ảnh để chọn làm icon.</p>
      </div>

      <div class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <span>Banner (ảnh nền)</span>
          <span class="text-slate-400" id="bannerPickerCurrent"></span>
        </span>
        <div class="flex flex-wrap items-center gap-2 mb-2 mt-1">
          <span class="text-xs text-slate-500">Thư mục ảnh:</span>
          <select id="f_banner_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 min-w-0">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnBannerRefreshFolders" class="btn btn-xs neon-edit">↻</button>
          <button type="button" id="btnDeleteBannerFolder" class="btn btn-xs neon-delete" title="Xoá thư mục hiện tại"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg></button>
          <div class="relative" id="bannerAddDropdown">
            <button type="button" id="btnBannerAdd" class="btn btn-xs neon-edit">+</button>
            <div id="bannerAddMenu" class="hidden absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg z-10 min-w-[140px]">
              <button type="button" id="btnBannerNewFolder" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-t-md">📁 Thêm thư mục</button>
              <button type="button" id="btnBannerUpload" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-b-md">⬆ Upload ảnh</button>
            </div>
          </div>
          <input type="file" id="f_banner_upload" accept="image/*" multiple class="hidden" />
          <input type="search" id="f_banner_search" placeholder="🔍 tìm ảnh..." class="text-xs px-2 py-1 rounded border border-slate-300" />
          <button type="button" id="btnBannerToggle" class="btn btn-xs neon-edit ml-auto">Hiện ảnh</button>
        </div>
        <div id="bannerPickerGrid" class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 hidden"></div>
        <input type="hidden" id="f_banner" value="${escapeHtml(pkg.banner || '')}" />
        <p class="text-xs text-slate-400 mt-1">Bấm vào ảnh để chọn làm banner.</p>
      </div>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_use_default_screens" ${pkg.__use_default_screens ? 'checked' : ''} />
          Dùng danh sách screenshot mặc định
          <span class="text-slate-400">(4 ảnh: preview-first → preview-four)</span>
        </span>
      </label>
      <div class="block md:col-span-2" id="screensListWrap" style="${pkg.__use_default_screens ? 'display:none' : ''}">
        <div class="flex flex-wrap items-center gap-2 mb-2">
          <span class="text-xs text-slate-500">Thư mục ảnh:</span>
          <select id="f_screen_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm flex-1 min-w-0">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnRefreshFolders" class="btn btn-xs neon-edit">↻</button>
          <button type="button" id="btnDeleteScreenFolder" class="btn btn-xs neon-delete" title="Xoá thư mục hiện tại"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg></button>
          <div class="relative" id="screenAddDropdown">
            <button type="button" id="btnScreenAdd" class="btn btn-xs neon-edit">+</button>
            <div id="screenAddMenu" class="hidden absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-md shadow-lg z-10 min-w-[140px]">
              <button type="button" id="btnNewFolder" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-t-md">📁 Thêm thư mục</button>
              <button type="button" id="btnUploadImages" class="w-full text-left px-3 py-2 text-xs neon-edit rounded-b-md">⬆ Upload ảnh</button>
            </div>
          </div>
          <input type="file" id="f_image_upload" accept="image/*" multiple class="hidden" />
          <input type="search" id="f_screen_search" placeholder="🔍 tìm ảnh..." class="text-xs px-2 py-1 rounded border border-slate-300" />
          <span id="screenCount" class="text-xs text-slate-400 ml-auto"></span>
        </div>
        <div id="screensGrid" class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2"></div>
        <p class="text-xs text-slate-400 mt-1">Bấm để chọn / bỏ chọn. Kéo thả để sắp xếp thứ tự.</p>
      </div>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_use_default_os" ${pkg.__use_default_os ? 'checked' : ''} />
          Dùng iOS rule mặc định (17.0 → 27.0)
        </span>
      </label>
      <div id="f_ios_custom_wrap" class="md:col-span-2 grid grid-cols-2 gap-2" style="${pkg.__use_default_os ? 'display:none' : ''}">
        <label class="block">
          <span class="text-xs text-slate-500">Hỗ trợ từ iOS (minimum)</span>
          <input id="f_ios_min" type="number" step="0.1" min="1" max="30" value="${escapeHtml(pkg.os_minimum ?? '17.0')}" placeholder="17.0" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
        </label>
        <label class="block">
          <span class="text-xs text-slate-500">Đến iOS (maximum)</span>
          <input id="f_ios_max" type="number" step="0.1" min="1" max="30" value="${escapeHtml(pkg.os_maximum ?? '27.0')}" placeholder="27.0" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
        </label>
      </div>

      <label class="block">
        <span class="text-xs text-slate-500">SHA-256 *</span>
        <input id="f_sha256" value="${escapeHtml(pkg.sha256)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Size (bytes) *</span>
        <input id="f_size" type="number" value="${pkg.size || 0}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Password (để trống nếu không cần)</span>
        <input id="f_password" value="${escapeHtml(pkg.password || '')}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <label class="block md:col-span-2 flex items-center gap-4">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_featured" ${pkg.featured ? 'checked' : ''} /> Featured
        </span>
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_isPrivate" ${pkg.isPrivate ? 'checked' : ''} /> Riêng tư
        </span>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Description (mô tả dài, xuống dòng thoải mái)</span>
        <textarea id="f_description" rows="6" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${escapeHtml(pkg.description || '')}</textarea>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Changelog</span>
        <textarea id="f_changelog" rows="3" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${escapeHtml(pkg.changelog || '')}</textarea>
      </label>

      <details class="md:col-span-2 text-xs text-slate-500">
        <summary class="cursor-pointer text-slate-600 hover:text-slate-900">📂 Mặc định dùng chung</summary>
        <div class="mt-2 p-3 bg-slate-50 rounded-md font-mono text-[11px] whitespace-pre-wrap">iOS rules:
${(window.DEFAULT_OS_RULES || []).map(r => '  - minimum: ' + r.minimum + ', maximum: ' + r.maximum + (r.builds ? ', builds: ' + JSON.stringify(r.builds) : '')).join('\n')}

Screenshots mặc định:
${(defaultScreens).map(s => '  - ' + s).join('\n')}</div>
      </details>
    </div>
  `;
}

// Module-level state cho screenshots grid trong modal
let currentSelectedScreens = [];
let currentScreenFolder = '';   // subfolder hiện tại đang xem ('' = root)
let currentFolderFolders = [];  // cache cây folder
let currentIconFolder = '';     // folder hiện tại cho icon picker
let currentBannerFolder = '';   // folder hiện tại cho banner picker

function _flattenFolders(tree) {
  const out = [];
  function walk(nodes, prefix) {
    nodes.forEach(f => {
      const p = prefix ? `${prefix}/${f.name}` : f.name;
      out.push({ path: p, name: f.name, depth: p.split('/').length });
      if (f.children && f.children.length) walk(f.children, p);
    });
  }
  walk(tree, '');
  return out;
}

async function loadFoldersIntoSelect() {
  try {
    const data = await api(`/api/repo/${state.currentRepo}/folders`);
    currentFolderFolders = data.folders || [];
    const flat = _flattenFolders(currentFolderFolders);
    // Screens picker
    const sel = $('#f_screen_folder');
    if (sel) {
      sel.innerHTML = '<option value="">— root (assets/) —</option>';
      flat.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.path;
        opt.textContent = '— '.repeat(f.depth - 1) + f.name;
        sel.appendChild(opt);
      });
      // Mặc định suggest thư mục 'preview' cho screens nếu tồn tại
      if (!currentScreenFolder) {
        const def = flat.find(f => f.path === 'preview');
        if (def) currentScreenFolder = 'preview';
      }
      sel.value = currentScreenFolder;
    }
    // Icon picker
    const selIcon = $('#f_icon_folder');
    if (selIcon) {
      selIcon.innerHTML = '<option value="">— root (assets/) —</option>';
      flat.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.path;
        opt.textContent = '— '.repeat(f.depth - 1) + f.name;
        selIcon.appendChild(opt);
      });
      // Mặc định suggest thư mục 'icon' cho icon picker
      if (!currentIconFolder) {
        const def = flat.find(f => f.path === 'icon');
        if (def) currentIconFolder = 'icon';
      }
      selIcon.value = currentIconFolder;
    }
    // Banner picker
    const selBanner = $('#f_banner_folder');
    if (selBanner) {
      selBanner.innerHTML = '<option value="">— root (assets/) —</option>';
      flat.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.path;
        opt.textContent = '— '.repeat(f.depth - 1) + f.name;
        selBanner.appendChild(opt);
      });
      if (!currentBannerFolder) {
        const def = flat.find(f => f.path === 'banner');
        if (def) currentBannerFolder = 'banner';
      }
      selBanner.value = currentBannerFolder;
    }
  } catch (err) {
    console.warn('load folders failed:', err);
  }
}

async function initScreensGrid(initialScreens) {
  currentSelectedScreens = [...(initialScreens || [])];
  // Suy ra folder từ icon/banner path nếu có, để grid hiển thị thẳng folder đó
  const initIcon = state.editingIndex !== null ? (state.packages[state.editingIndex]?.icon || '') : '';
  const initBanner = state.editingIndex !== null ? (state.packages[state.editingIndex]?.banner || '') : '';
  if (initIcon && initIcon.startsWith('assets/')) currentIconFolder = initIcon.slice('assets/'.length).replace(/\/[^\/]+$/, '');
  if (initBanner && initBanner.startsWith('assets/')) currentBannerFolder = initBanner.slice('assets/'.length).replace(/\/[^\/]+$/, '');
  await loadFoldersIntoSelect();
  await refreshScreenGrid();
  await refreshIconPicker();
  await refreshBannerPicker();
  updatePickerCurrentLabels();
}

async function refreshIconPicker() {
  const grid = $('#iconPickerGrid');
  if (!grid) return;
  grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Đang tải...</p>';
  try {
    const data = await api(`/api/repo/${state.currentRepo}/folder-files?path=${encodeURIComponent(currentIconFolder)}`);
    const files = data.files || [];
    const selected = $('#f_icon')?.value || '';
    grid.innerHTML = '';
    if (files.length === 0) {
      grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Thư mục này chưa có ảnh. Upload hoặc chọn thư mục khác.</p>';
      return;
    }
    // Filter theo search input
    const q = ($('#f_icon_search')?.value || '').toLowerCase().trim();
    const filtered = q ? files.filter(p => p.toLowerCase().includes(q)) : files;
    if (filtered.length === 0) {
      grid.innerHTML = `<p class="text-xs text-slate-400 col-span-8">Không có ảnh nào khớp "${escapeHtml(q)}".</p>`;
      return;
    }
    filtered.forEach(path => {
      const item = document.createElement('div');
      const isSelected = path === selected;
      item.className = `relative border rounded-md overflow-hidden cursor-pointer aspect-square ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-slate-200 hover:border-blue-300'}`;
      item.title = path;
      const fileName = path.split('/').pop();
      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-blue-500/20 flex items-center justify-center"><span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(fileName)}</div>
        <button type="button" class="delete-asset-btn absolute top-1 right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" data-path="${encodeURIComponent(path)}" data-kind="image" title="Xoá ảnh">✕</button>
      `;
      item.classList.add('group');
      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-asset-btn')) { e.stopPropagation(); handleDeleteAsset(e.target); return; }
        selectIcon(path);
      });
      grid.appendChild(item);
    });
  } catch (err) {
    grid.innerHTML = `<p class="text-xs text-red-400 col-span-8">Lỗi: ${escapeHtml(err.message)}</p>`;
  }
}

async function handleDeleteAsset(btn) {
  const path = decodeURIComponent(btn.dataset.path || '');
  const kind = btn.dataset.kind || 'image';
  if (!confirm(`Xoá "${path}"? Hành động này không thể hoàn tác.`)) return;
  try {
    await api(`/api/repo/${state.currentRepo}/file?path=${encodeURIComponent(path)}&kind=${kind}`, { method: 'DELETE' });
    toast(`Đã xoá: ${path}`, 'success');
    await refreshIconPicker();
    await refreshBannerPicker();
    await refreshScreenGrid();
    const files = await api(`/api/repo/${state.currentRepo}/files`);
    state.assets = files.assets || [];
  } catch (err) {
    toast(`Lỗi xoá: ${err.message}`, 'error');
  }
}

async function refreshBannerPicker() {
  const grid = $('#bannerPickerGrid');
  if (!grid) return;
  grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Đang tải...</p>';
  try {
    const data = await api(`/api/repo/${state.currentRepo}/folder-files?path=${encodeURIComponent(currentBannerFolder)}`);
    const files = data.files || [];
    const selected = $('#f_banner')?.value || '';
    grid.innerHTML = '';
    if (files.length === 0) {
      grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Thư mục này chưa có ảnh. Upload hoặc chọn thư mục khác.</p>';
      return;
    }
    const q = ($('#f_banner_search')?.value || '').toLowerCase().trim();
    const filtered = q ? files.filter(p => p.toLowerCase().includes(q)) : files;
    if (filtered.length === 0) {
      grid.innerHTML = `<p class="text-xs text-slate-400 col-span-8">Không có ảnh nào khớp "${escapeHtml(q)}".</p>`;
      return;
    }
    filtered.forEach(path => {
      const item = document.createElement('div');
      const isSelected = path === selected;
      item.className = `relative border rounded-md overflow-hidden cursor-pointer aspect-square ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-slate-200 hover:border-blue-300'} group`;
      item.title = path;
      const fileName = path.split('/').pop();
      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-blue-500/20 flex items-center justify-center"><span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(fileName)}</div>
        <button type="button" class="delete-asset-btn absolute top-1 right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" data-path="${encodeURIComponent(path)}" data-kind="image" title="Xoá ảnh">✕</button>
      `;
      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-asset-btn')) { e.stopPropagation(); handleDeleteAsset(e.target); return; }
        selectBanner(path);
      });
      grid.appendChild(item);
    });
  } catch (err) {
    grid.innerHTML = `<p class="text-xs text-red-400 col-span-8">Lỗi: ${escapeHtml(err.message)}</p>`;
  }
}

function selectIcon(path) {
  const hidden = $('#f_icon');
  if (hidden) hidden.value = path;
  updatePickerCurrentLabels();
  refreshIconPicker();
  // Sau khi chọn ảnh xong → ẩn grid luôn cho gọn
  const grid = $('#iconPickerGrid');
  if (grid && !grid.classList.contains('hidden')) {
    grid.classList.add('hidden');
    const btn = $('#btnIconToggle');
    if (btn) btn.textContent = 'Hiện ảnh';
  }
}

function selectBanner(path) {
  const hidden = $('#f_banner');
  if (hidden) hidden.value = path;
  updatePickerCurrentLabels();
  refreshBannerPicker();
  // Sau khi chọn ảnh xong → ẩn grid luôn cho gọn
  const grid = $('#bannerPickerGrid');
  if (grid && !grid.classList.contains('hidden')) {
    grid.classList.add('hidden');
    const btn = $('#btnBannerToggle');
    if (btn) btn.textContent = 'Hiện ảnh';
  }
}

function updatePickerCurrentLabels() {
  const ic = $('#f_icon')?.value;
  const bn = $('#f_banner')?.value;
  const icLab = $('#iconPickerCurrent');
  const bnLab = $('#bannerPickerCurrent');
  if (icLab) icLab.textContent = ic ? `→ ${ic.split('/').pop()}` : '';
  if (bnLab) bnLab.textContent = bn ? `→ ${bn.split('/').pop()}` : '';
}

async function refreshScreenGrid() {
  const grid = $('#screensGrid');
  if (!grid) return;
  grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Đang tải...</p>';
  try {
    const data = await api(`/api/repo/${state.currentRepo}/folder-files?path=${encodeURIComponent(currentScreenFolder)}`);
    const files = data.files || [];
    grid.innerHTML = '';
    if (files.length === 0) {
      grid.innerHTML = '<p class="text-xs text-slate-400 col-span-8">Không có ảnh trong thư mục này.</p>';
      updateScreenCount();
      return;
    }
    const q = ($('#f_screen_search')?.value || '').toLowerCase().trim();
    const filtered = q ? files.filter(p => p.toLowerCase().includes(q)) : files;
    if (filtered.length === 0) {
      grid.innerHTML = `<p class="text-xs text-slate-400 col-span-8">Không có ảnh nào khớp "${escapeHtml(q)}".</p>`;
      updateScreenCount();
      return;
    }
    filtered.forEach(path => {
      const isSelected = currentSelectedScreens.includes(path);
      const item = document.createElement('div');
      item.className = 'relative group aspect-video rounded-lg overflow-hidden border-2 cursor-pointer select-none ' +
        (isSelected ? 'border-green-500 ring-2 ring-green-300' : 'border-slate-200 hover:border-slate-400');
      item.dataset.path = path;
      item.draggable = true;
      item.title = path;
      const fileName = path.split('/').pop();
      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-green-500/30 flex items-center justify-center check-overlay"><span class="bg-green-500 text-white text-xs px-1.5 py-0.5 rounded font-bold">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(fileName)}</div>
        <button type="button" class="delete-asset-btn absolute top-1 right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" data-path="${encodeURIComponent(path)}" data-kind="image" title="Xoá ảnh">✕</button>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-asset-btn')) { e.stopPropagation(); handleDeleteAsset(e.target); return; }
        const idx = currentSelectedScreens.indexOf(path);
        if (idx >= 0) {
          currentSelectedScreens.splice(idx, 1);
        } else {
          currentSelectedScreens.push(path);
        }
        item.classList.toggle('border-green-500', currentSelectedScreens.includes(path));
        item.classList.toggle('ring-4', currentSelectedScreens.includes(path));
        item.classList.toggle('ring-green-400', currentSelectedScreens.includes(path));
        item.classList.toggle('border-slate-200', !currentSelectedScreens.includes(path));
        const overlay = item.querySelector('.check-overlay');
        if (currentSelectedScreens.includes(path)) {
          if (!overlay) {
            const div = document.createElement('div');
            div.className = 'absolute inset-0 bg-green-500/30 flex items-center justify-center check-overlay';
            div.innerHTML = '<span class="bg-green-500 text-white text-xs px-1.5 py-0.5 rounded font-bold">✓</span>';
            item.appendChild(div);
          }
        } else if (overlay) {
          overlay.remove();
        }
        updateScreenCount();
      });

      item.addEventListener('dragstart', e => {
        e.dataTransfer.setData('text/plain', path);
        item.classList.add('opacity-50');
      });
      item.addEventListener('dragend', () => {
        item.classList.remove('opacity-50');
      });
      item.addEventListener('dragover', e => {
        e.preventDefault();
        item.classList.add('ring-2', 'ring-blue-400');
      });
      item.addEventListener('dragleave', () => {
        item.classList.remove('ring-2', 'ring-blue-400');
      });
      item.addEventListener('drop', e => {
        e.preventDefault();
        item.classList.remove('ring-2', 'ring-blue-400');
        const fromPath = e.dataTransfer.getData('text/plain');
        if (fromPath === path) return;
        const fromIdx = currentSelectedScreens.indexOf(fromPath);
        const toIdx = currentSelectedScreens.indexOf(path);
        if (fromIdx >= 0 && toIdx >= 0) {
          currentSelectedScreens.splice(fromIdx, 1);
          currentSelectedScreens.splice(toIdx, 0, fromPath);
          updateScreenCount();
        }
      });

      grid.appendChild(item);
    });
    updateScreenCount();
  } catch (err) {
    grid.innerHTML = `<p class="text-xs text-red-500 col-span-8">Lỗi: ${escapeHtml(err.message)}</p>`;
  }
}

function updateScreenCount() {
  const el = $('#screenCount');
  if (el) el.textContent = `${currentSelectedScreens.length} ảnh đã chọn`;
}

function bindFormEvents() {
  // ====== PublishedAt: checkbox toggle + auto now ======
  const noPubChk = $('#f_no_publishedAt');
  const pubBox = $('#publishedAtBox');
  const pubInput = $('#f_publishedAt');
  const btnNow = $('#btnNowPublishedAt');

  const togglePubBox = () => {
    pubBox?.classList.toggle('hidden', noPubChk?.checked ?? false);
  };
  noPubChk?.addEventListener('change', togglePubBox);
  btnNow?.addEventListener('click', () => {
    // Fill current time in local format for datetime-local input
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    pubInput.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    noPubChk.checked = false;
    pubBox.classList.remove('hidden');
  });
  // Init: if pkg has no publishedAt → check the box; else pre-fill
  {
    const val = state.editingIndex !== null ? (state.packages[state.editingIndex]?.publishedAt || '') : '';
    if (!val) { noPubChk.checked = true; pubBox.classList.add('hidden'); }
    else {
      // Parse ISO string to datetime-local value
      try {
        const d = new Date(val);
        const pad = n => String(n).padStart(2, '0');
        pubInput.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      } catch { pubInput.value = val; }
    }
  }

  $('#btnAutoFill')?.addEventListener('click', async () => {
    const path = $('#f_download').value;
    if (!path) { toast('Chọn file .3105 trước đã.', 'error'); return; }
    try {
      const r = await api(`/api/repo/${state.currentRepo}/hash`, {
        method: 'POST',
        body: JSON.stringify({ path }),
      });
      $('#f_download').value = (r.path || '').replace(/^packages\//, '');
      $('#f_sha256').value = r.sha256;
      $('#f_size').value = r.size;
      if (typeof syncDlClearBtn === 'function') syncDlClearBtn();
      toast(`Đã lấy hash + size cho ${r.path}`, 'success');
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });

  $('#f_use_default_screens')?.addEventListener('change', e => {
    $('#screensListWrap').style.display = e.target.checked ? 'none' : 'block';
    // Khi bỏ tick default → xóa 4 ảnh preview cũ để tránh dính ảnh thừa
    if (!e.target.checked) {
      currentSelectedScreens.length = 0;
      updateScreenCount();
      // Bỏ highlight tất cả ảnh
      document.querySelectorAll('.screen-thumb').forEach(el => {
        el.classList.remove('ring-2', 'ring-green-500');
      });
    }
  });

  // iOS: tick "mặc định" -> ẩn 2 ô min/max; bỏ tick -> hiện
  // Set cả inline display:none AND thêm attribute để CSS rule [style*="display:none"] chắc chắn match
  const setIosWrap = (hide) => {
    const wrap = $('#f_ios_custom_wrap');
    if (!wrap) return;
    wrap.style.display = hide ? 'none' : '';
    if (hide) wrap.setAttribute('data-hidden', '1');
    else wrap.removeAttribute('data-hidden');
  };
  $('#f_use_default_os')?.addEventListener('change', e => {
    setIosWrap(e.target.checked);
  });

  // Search input: gõ → auto bật grid + filter; xoá hết → ẩn grid lại
  const autoShow = (gridId, toggleId) => {
    const grid = $(gridId);
    const btn = $(toggleId);
    if (grid?.classList.contains('hidden') && btn) {
      btn.click();
    }
  };
  const autoHide = (gridId, toggleId) => {
    const grid = $(gridId);
    const btn = $(toggleId);
    if (!grid?.classList.contains('hidden') && btn) {
      btn.click();
    }
  };
  $('#f_icon_search')?.addEventListener('input', function () {
    if (this.value.trim()) { autoShow('#iconPickerGrid', '#btnIconToggle'); refreshIconPicker(); }
    else { refreshIconPicker(); /* reload đầy đủ khi clear search */ }
  });
  $('#f_banner_search')?.addEventListener('input', function () {
    if (this.value.trim()) { autoShow('#bannerPickerGrid', '#btnBannerToggle'); refreshBannerPicker(); }
    else { refreshBannerPicker(); }
  });
  $('#f_screen_search')?.addEventListener('input', function () {
    if (this.value.trim()) { refreshScreenGrid(); }
    else { autoHide('#screensGrid', '#btnRefreshFolders'); }
  });

  // Upload file .3105 - drag-drop + click
  const uploadZone = $('#pkgUploadZone');
  const fileInput = $('#f_pkg_upload');
  if (uploadZone && fileInput) {
    uploadZone.addEventListener('click', () => fileInput.click());
    ['dragover', 'dragenter'].forEach(evt => {
      uploadZone.addEventListener(evt, e => {
        e.preventDefault();
        uploadZone.classList.add('border-blue-500', 'bg-blue-50');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      uploadZone.addEventListener(evt, e => {
        e.preventDefault();
        uploadZone.classList.remove('border-blue-500', 'bg-blue-50');
      });
    });
    uploadZone.addEventListener('drop', async e => {
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length > 0) await uploadPackages(files);
    });
    fileInput.addEventListener('change', async e => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) await uploadPackages(files);
      e.target.value = '';
    });
  }

  // ====== Combobox tìm kiếm file .3105 ======
  const dlInput = $('#f_download');
  const dlMenu = $('#f_download_menu');
  const dlClear = $('#f_download_clear');

  function renderDlMenu(query) {
    const q = (query || '').trim().toLowerCase();
    const all = Array.isArray(state.packageFiles) ? state.packageFiles : [];
    const matches = q
      ? all.filter(p => p.toLowerCase().includes(q))
      : all;
    if (!dlMenu) return;
    if (matches.length === 0) {
      dlMenu.innerHTML = '<div class="px-3 py-2 text-slate-400">Không có file .3105 nào</div>';
    } else {
      dlMenu.innerHTML = matches.map(p => {
        const hl = q ? escapeHtml(p).replace(new RegExp(escapeReg(q), 'ig'),
          m => `<mark class="dl-hl">${m}</mark>`) : escapeHtml(p);
        return `<button type="button" data-val="${escapeHtml(p)}"
          class="dl-item block w-full text-left px-3 py-1.5 truncate">${hl}</button>`;
      }).join('');
    }
  }

  function openDlMenu() {
    if (!dlMenu) return;
    renderDlMenu(dlInput.value);
    dlMenu.classList.add('show');
  }
  function closeDlMenu() {
    if (!dlMenu) return;
    dlMenu.classList.remove('show');
  }

  if (dlInput && dlMenu) {
    dlInput.addEventListener('focus', openDlMenu);
    dlInput.addEventListener('input', () => {
      syncDlClearBtn();
      openDlMenu();
    });
    dlInput.addEventListener('keydown', e => {
      if (e.key === 'Escape') { closeDlMenu(); dlInput.blur(); }
    });
    dlMenu.addEventListener('mousedown', e => {
      // mousedown để input không mất focus trước khi click xử lý
      const btn = e.target.closest('button[data-val]');
      if (!btn) return;
      e.preventDefault();
      dlInput.value = btn.dataset.val;
      closeDlMenu();
      syncDlClearBtn();
      dlInput.focus();
    });
  }
  dlClear?.addEventListener('click', () => {
    if (!dlInput) return;
    dlInput.value = '';
    syncDlClearBtn();
    openDlMenu();
    dlInput.focus();
  });
  document.addEventListener('click', e => {
    if (!dlMenu || !dlInput) return;
    if (e.target === dlInput || dlMenu.contains(e.target) || dlClear?.contains(e.target)) return;
    closeDlMenu();
  });

  async function uploadPackages(files) {
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    try {
      const r = await api(`/api/repo/${state.currentRepo}/upload?kind=package`, {
        method: 'POST',
        body: fd,
      });
      toast(`Đã upload ${r.saved.length} file .3105 vào packages/.`, 'success');
      // Refresh danh sách package file
      const list = await api(`/api/repo/${state.currentRepo}/files`);
      state.packageFiles = (list.packages || []).map(p => p.replace(/^packages\//, ''));
      // Cập nhật lại <select id="f_download"> mà không re-render toàn bộ form
      const sel = $('#f_download');
      if (sel) {
        const saved = r.saved || [];
        const firstSaved = saved.length > 0 ? saved[0].replace('packages/', '') : '';
        if (firstSaved && state.packageFiles.includes(firstSaved)) {
          sel.value = firstSaved;
          sel.focus();
          if (typeof renderDlMenu === 'function') renderDlMenu(firstSaved);
          if (typeof syncDlClearBtn === 'function') syncDlClearBtn();
        }
      }
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  }

  $('#f_screen_folder')?.addEventListener('change', e => {
    currentScreenFolder = e.target.value;
    refreshScreenGrid();
  });

  // ====== Xoá thư mục (Icon / Banner / Screen) ======
  const deleteFolder = async (folder, setterFn) => {
    if (!folder) return;
    if (!confirm(`Xoá thư mục "${folder}" và toàn bộ nội dung bên trong? Hành động này không thể hoàn tác.`)) return;
    try {
      await api(`/api/repo/${state.currentRepo}/file?path=${encodeURIComponent(folder)}&kind=image`, { method: 'DELETE' });
      toast(`Đã xoá thư mục: ${folder}`, 'success');
      setterFn('');  // reset về root
      await loadFoldersIntoSelect();
      await refreshIconPicker();
      await refreshBannerPicker();
      await refreshScreenGrid();
    } catch (err) {
      toast(`Lỗi xoá thư mục: ${err.message}`, 'error');
    }
  };
  $('#btnDeleteIconFolder')?.addEventListener('click', () => deleteFolder(currentIconFolder, v => { currentIconFolder = v; }));
  $('#btnDeleteBannerFolder')?.addEventListener('click', () => deleteFolder(currentBannerFolder, v => { currentBannerFolder = v; }));
  $('#btnDeleteScreenFolder')?.addEventListener('click', () => deleteFolder(currentScreenFolder, v => { currentScreenFolder = v; }));
  $('#btnDeletePackageFile')?.addEventListener('click', async () => {
    const path = $('#f_download')?.value;
    if (!path) return;
    if (!confirm(`Xoá file "${path}"? Không thể hoàn tác.`)) return;
    try {
      await api(`/api/repo/${state.currentRepo}/file?path=${encodeURIComponent('packages/' + path)}&kind=package`, { method: 'DELETE' });
      toast(`Đã xoá: ${path}`, 'success');
      $('#f_download').value = '';
      $('#f_sha256').value = '';
      $('#f_size').value = '';
      const list = await api(`/api/repo/${state.currentRepo}/files`);
      state.packageFiles = (list.packages || []).map(p => p.replace(/^packages\//, ''));
      if (typeof syncDlClearBtn === 'function') syncDlClearBtn();
    } catch (err) {
      toast(`Lỗi xoá: ${err.message}`, 'error');
    }
  });

  $('#btnRefreshFolders')?.addEventListener('click', async () => {
    await loadFoldersIntoSelect();
    await refreshScreenGrid();
  });

  $('#btnNewFolder')?.addEventListener('click', async () => {
    const name = prompt('Tên thư mục mới (vd: owen-013, hdr, v.v):');
    if (!name) return;
    // Nếu đang ở subfolder thì tạo con
    const path = currentScreenFolder ? `${currentScreenFolder}/${name}` : name;
    try {
      await api(`/api/repo/${state.currentRepo}/mkdir`, {
        method: 'POST',
        body: JSON.stringify({ folder: path }),
      });
      toast(`Đã tạo thư mục "${path}"`, 'success');
      currentScreenFolder = path;
      await loadFoldersIntoSelect();
      await refreshScreenGrid();
      // Refresh toàn bộ asset list cho icon/banner
      const files = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = files.assets || [];
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });

  $('#btnUploadImages')?.addEventListener('click', () => {
    $('#f_image_upload').click();
  });

  $('#f_image_upload')?.addEventListener('change', async e => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    try {
      const r = await api(`/api/repo/${state.currentRepo}/upload?kind=image&folder=${encodeURIComponent(currentScreenFolder)}`, {
        method: 'POST',
        body: fd,
      });
      toast(`Đã upload ${r.saved.length} ảnh vào ${currentScreenFolder || 'assets/'}.`, 'success');
      // Refresh asset list
      const list = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = list.assets || [];
      await refreshScreenGrid();
      await refreshIconPicker();
      await refreshBannerPicker();
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    } finally {
      e.target.value = ''; // reset để có thể chọn lại cùng file
    }
  });

  // ====== Dropdown + (Thêm thư mục / Upload ảnh) ======
  const setupDropdown = (btnId, menuId) => {
    const btn = $(btnId);
    const menu = $(menuId);
    if (!btn || !menu) return;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close other menus
      $$('[id$="AddMenu"]').forEach(m => { if (m !== menu) m.classList.add('hidden'); });
      menu.classList.toggle('hidden');
    });
  };
  setupDropdown('#btnIconAdd', '#iconAddMenu');
  setupDropdown('#btnBannerAdd', '#bannerAddMenu');
  setupDropdown('#btnScreenAdd', '#screenAddMenu');
  // Close menus on outside click
  document.addEventListener('click', () => $$('[id$="AddMenu"]').forEach(m => m.classList.add('hidden')));

  // ====== Icon picker handlers ======
  $('#f_icon_folder')?.addEventListener('change', e => {
    currentIconFolder = e.target.value;
    refreshIconPicker();
  });
  $('#btnIconRefreshFolders')?.addEventListener('click', async () => {
    await loadFoldersIntoSelect();
    await refreshIconPicker();
  });
  $('#btnIconNewFolder')?.addEventListener('click', async () => {
    const name = prompt('Tên thư mục mới cho icon (sẽ tạo bên trong thư mục hiện tại):');
    if (!name) return;
    const path = currentIconFolder ? `${currentIconFolder}/${name}` : name;
    try {
      await api(`/api/repo/${state.currentRepo}/mkdir`, {
        method: 'POST',
        body: JSON.stringify({ folder: path }),
      });
      toast(`Đã tạo thư mục "${path}"`, 'success');
      currentIconFolder = path;
      await loadFoldersIntoSelect();
      await refreshIconPicker();
      const files = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = files.assets || [];
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });
  $('#btnIconUpload')?.addEventListener('click', () => $('#f_icon_upload').click());
  $('#f_icon_upload')?.addEventListener('change', async e => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    try {
      const r = await api(`/api/repo/${state.currentRepo}/upload?kind=image&folder=${encodeURIComponent(currentIconFolder)}`, {
        method: 'POST',
        body: fd,
      });
      toast(`Đã upload ${r.saved.length} ảnh vào ${currentIconFolder || 'assets/'}.`, 'success');
      const list = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = list.assets || [];
      await refreshIconPicker();
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    } finally {
      e.target.value = '';
    }
  });
  $('#btnIconToggle')?.addEventListener('click', () => {
    const grid = $('#iconPickerGrid');
    if (!grid) return;
    grid.classList.toggle('hidden');
    const btn = $('#btnIconToggle');
    btn.textContent = grid.classList.contains('hidden') ? 'Hiện ảnh' : 'Ẩn ảnh';
  });

  // ====== Banner picker handlers ======
  $('#f_banner_folder')?.addEventListener('change', e => {
    currentBannerFolder = e.target.value;
    refreshBannerPicker();
  });
  $('#btnBannerRefreshFolders')?.addEventListener('click', async () => {
    await loadFoldersIntoSelect();
    await refreshBannerPicker();
  });
  $('#btnBannerNewFolder')?.addEventListener('click', async () => {
    const name = prompt('Tên thư mục mới cho banner (sẽ tạo bên trong thư mục hiện tại):');
    if (!name) return;
    const path = currentBannerFolder ? `${currentBannerFolder}/${name}` : name;
    try {
      await api(`/api/repo/${state.currentRepo}/mkdir`, {
        method: 'POST',
        body: JSON.stringify({ folder: path }),
      });
      toast(`Đã tạo thư mục "${path}"`, 'success');
      currentBannerFolder = path;
      await loadFoldersIntoSelect();
      await refreshBannerPicker();
      const files = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = files.assets || [];
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });
  $('#btnBannerUpload')?.addEventListener('click', () => $('#f_banner_upload').click());
  $('#f_banner_upload')?.addEventListener('change', async e => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    try {
      const r = await api(`/api/repo/${state.currentRepo}/upload?kind=image&folder=${encodeURIComponent(currentBannerFolder)}`, {
        method: 'POST',
        body: fd,
      });
      toast(`Đã upload ${r.saved.length} ảnh vào ${currentBannerFolder || 'assets/'}.`, 'success');
      const list = await api(`/api/repo/${state.currentRepo}/files`);
      state.assets = list.assets || [];
      await refreshBannerPicker();
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    } finally {
      e.target.value = '';
    }
  });
  $('#btnBannerToggle')?.addEventListener('click', () => {
    const grid = $('#bannerPickerGrid');
    if (!grid) return;
    grid.classList.toggle('hidden');
    const btn = $('#btnBannerToggle');
    btn.textContent = grid.classList.contains('hidden') ? 'Hiện ảnh' : 'Ẩn ảnh';
  });

  // Init screenshots grid sau khi form HTML đã render
  const initScreens = state.editingIndex !== null
    ? (state.packages[state.editingIndex]?.screenshots || [])
    : [];
  initScreensGrid(initScreens);

  $('#btnSavePackage').onclick = savePackageFromForm;
  $('#btnCancel').onclick = closeModal;
  $('#btnCloseModal').onclick = closeModal;
}

function readFormToPackage() {
  return {
    identifier: $('#f_identifier').value.trim(),
    name: $('#f_name').value.trim(),
    version: $('#f_version').value.trim(),
    author: $('#f_author').value.trim(),
    summary: $('#f_summary').value.trim(),
    category: $('#f_category').value,
    tags: $('#f_tags').value.split(',').map(s => s.trim()).filter(Boolean),
    kind: $('#f_kind').value.trim(),
    publishedAt: $('#f_no_publishedAt').checked ? '' : ($('#f_publishedAt').value ? new Date($('#f_publishedAt').value).toISOString() : ''),
    icon: $('#f_icon').value,
    banner: $('#f_banner').value,
    __use_default_screens: $('#f_use_default_screens').checked,
    screenshots: currentSelectedScreens.slice(),
    download: (() => {
      const v = $('#f_download').value.trim();
      if (!v) return '';
      // Nếu người dùng lỡ gõ đường dẫn đầy đủ, strip về tên file
      const fileName = v.replace(/^packages\//, '').replace(/^.*[\\\/]/, '');
      return fileName ? `packages/${fileName}` : '';
    })(),
    sha256: normalizeSha256($('#f_sha256').value),
    size: parseInt($('#f_size').value, 10) || 0,
    password: $('#f_password').value,
    featured: $('#f_featured').checked,
    isPrivate: $('#f_isPrivate').checked,
    __use_default_os: $('#f_use_default_os').checked,
    os_minimum: $('#f_ios_min')?.value.trim() || '',
    os_maximum: $('#f_ios_max')?.value.trim() || '',
    description: $('#f_description').value,
    changelog: $('#f_changelog').value,
  };
}

function savePackageFromForm() {
  const pkg = readFormToPackage();
  // Validate
  if (!pkg.identifier) return toast('Thiếu identifier.', 'error');
  if (!/^[a-z0-9][a-z0-9._-]{1,63}$/.test(pkg.identifier)) return toast('Identifier không hợp lệ.', 'error');
  if (!pkg.name) return toast('Thiếu tên.', 'error');
  if (!pkg.download) return toast('Thiếu file .3105.', 'error');
  if (!pkg.sha256) return toast('Thiếu SHA-256 (bấm "Tự động điền").', 'error');
  if (!/^[0-9A-F]{64}$/.test(pkg.sha256)) return toast('SHA-256 phải là hex 64 ký tự.', 'error');
  if (!pkg.size || pkg.size <= 0) return toast('Size không hợp lệ.', 'error');

  // Trùng identifier với package khác?
  const dup = state.packages.findIndex((p, i) =>
    p.identifier === pkg.identifier && i !== state.editingIndex);
  if (dup >= 0) return toast(`Identifier "${pkg.identifier}" đã tồn tại ở package #${dup + 1}.`, 'error');

  // Tách các trường nội bộ ra khỏi object lưu trữ
  const useOs = pkg.__use_default_os;
  const useScreens = pkg.__use_default_screens;
  const pkgClean = { ...pkg };
  delete pkgClean.__use_default_os;
  delete pkgClean.__use_default_screens;
  // Nếu user bỏ check "dùng iOS rule mặc định" → ghi rõ supportedOS vào package
  if (!useOs) {
    const min = parseFloat(pkgClean.os_minimum) || 0;
    const max = parseFloat(pkgClean.os_maximum) || 0;
    pkgClean.supportedOS = [{ minimum: String(min), maximum: String(max) }];
  } else {
    delete pkgClean.supportedOS;
  }

  // Nếu user check "dùng danh sách screenshot mặc định" → ghi đúng sharedScreens
  // để khi load lại khớp với anchor backend.
  if (useScreens) {
    pkgClean.screenshots = (state.sharedScreens || []).slice();
  } else {
    // Giữ nguyên currentSelectedScreens như đã chuẩn hoá ở pkg object
  }
  delete pkgClean.os_minimum;
  delete pkgClean.os_maximum;

  if (state.editingIndex === null) {
    state.packages.push(pkgClean);
    state.packagesMeta.push({
      use_anchor_os: useOs,
      use_anchor_screens: useScreens,
    });
    // Gắn cờ __use_default_* cho package mới để mở edit lại render đúng
    state.packages[state.packages.length - 1].__use_default_os = useOs;
    state.packages[state.packages.length - 1].__use_default_screens = useScreens;
    // Ghi nhận added
    state.changes.added.push({
      identifier: pkgClean.identifier,
      name: pkgClean.name || pkgClean.identifier,
    });
  } else {
    state.packages[state.editingIndex] = pkgClean;
    state.packagesMeta[state.editingIndex] = {
      use_anchor_os: useOs,
      use_anchor_screens: useScreens,
    };
    // Đồng bộ lại cờ __use_default_* để lần mở edit sau checkbox render đúng
    state.packages[state.editingIndex].__use_default_os = useOs;
    state.packages[state.editingIndex].__use_default_screens = useScreens;
    // Ghi nhận edited
    state.changes.edited.push({
      identifier: pkgClean.identifier,
      name: pkgClean.name || pkgClean.identifier,
    });
  }
  closeModal();
  renderPackageList();
  toast(`Đã lưu package "${pkgClean.identifier}" vào bộ nhớ tạm. Bấm "🚀 Lưu & Push Git" để ghi ra repo.yml.`, 'success');
}

function deletePackage(idx) {
  const pkg = state.packages[idx];
  if (!confirm(`Xoá package "${pkg.identifier}" (${pkg.name || ''})?`)) return;
  // Ghi nhận deleted
  state.changes.deleted.push({
    identifier: pkg.identifier,
    name: pkg.name || pkg.identifier,
  });
  state.packages.splice(idx, 1);
  state.packagesMeta.splice(idx, 1);
  renderPackageList();
  toast(`Đã xoá "${pkg.identifier}" khỏi bộ nhớ tạm.`, 'info');
}

function duplicatePackage(idx) {
  const src = state.packages[idx];
  const used = new Set(state.packages.map(p => p.identifier));
  let n = 1;
  let newId = `${src.identifier}-copy`;
  while (used.has(newId)) {
    n += 1;
    newId = `${src.identifier}-copy${n}`;
  }
  const copy = {
    ...src,
    identifier: newId,
    name: `${src.name} (bản sao)`,
    sha256: '',
    size: 0,
    download: '',
  };
  state.packages.splice(idx + 1, 0, copy);
  state.packagesMeta.splice(idx + 1, 0, {
    use_anchor_os: state.packagesMeta[idx]?.use_anchor_os ?? true,
    use_anchor_screens: state.packagesMeta[idx]?.use_anchor_screens ?? true,
  });
  renderPackageList();
  toast(`Đã sao chép package → ${newId}. Mở Sửa để điền SHA-256/file mới.`, 'success');
}

// ---------------------------------------------------------------------
// Save to YAML
// ---------------------------------------------------------------------

function buildCommitMessage() {
  // Sinh commit message kiểu: "Add ow-001 PUBG ALL", "Update ow-005, ow-007", "Remove ow-009"
  const parts = [];
  const fmtList = (items, prefix) => {
    if (items.length === 0) return '';
    if (items.length === 1) return `${prefix} ${items[0].identifier} (${items[0].name})`;
    if (items.length <= 3) {
      const ids = items.map(i => i.identifier).join(', ');
      return `${prefix} ${ids}`;
    }
    return `${prefix} ${items.length} packages`;
  };
  const a = fmtList(state.changes.added, 'Add');
  const e = fmtList(state.changes.edited, 'Update');
  const d = fmtList(state.changes.deleted, 'Remove');
  [a, e, d].forEach(p => { if (p) parts.push(p); });
  if (parts.length === 0) {
    return `Update ${state.currentRepo}`;
  }
  return parts.join('; ');
}

async function saveAll() {
  if (!state.currentRepo) return toast('Chưa chọn repo.', 'error');

  // Đồng bộ meta packagesMeta cho khớp số lượng
  while (state.packagesMeta.length < state.packages.length) {
    state.packagesMeta.push({ use_anchor_os: true, use_anchor_screens: true });
  }
  if (state.packagesMeta.length > state.packages.length) {
    state.packagesMeta.length = state.packages.length;
  }

  // Đọc meta từ form
  const repoMeta = {
    schemaVersion: 1,
    identifier: $('#meta_identifier').value.trim() || `com.owen.${state.currentRepo}`,
    name: $('#meta_name').value.trim() || `${state.currentRepo} Repository`,
    description: $('#meta_description').value.trim(),
    icon: $('#meta_icon').value,
    accentColor: $('#meta_accentColor').value.trim() || '#FF3B30',
  };

  // Bước 1: Ghi file YAML
  const btn = $('#btnSave');
  btn.disabled = true;
  btn.dataset.loading = '1';
  btn.textContent = '';

  // Hiển thị modal tiến trình 4 bước: pull → add → status → commit → push
  const steps = [
    { id: 'save', label: 'Ghi file YAML', status: 'pending' },
    { id: 'pull', label: 'git pull origin main', status: 'pending' },
    { id: 'add',  label: 'git add -A',           status: 'pending' },
    { id: 'status', label: 'git status (kiểm tra)', status: 'pending' },
    { id: 'commit', label: 'git commit',           status: 'pending' },
    { id: 'push',   label: 'git push origin main', status: 'pending' },
  ];
  showPushProgressModal(steps);

  try {
    // Bước 1: Ghi YAML
    setStepStatus('save', 'running');
    const r = await api(`/api/repo/${state.currentRepo}/save`, {
      method: 'POST',
      body: JSON.stringify({
        repoMeta,
        packages: state.packages,
        packagesMeta: state.packagesMeta,
      }),
    });
    const anchors = r.anchors || {};
    const anchorInfo = (anchors.os || anchors.screens) ? ` (anchor: ${[anchors.os && 'os', anchors.screens && 'screens'].filter(Boolean).join('+')})` : '';
    setStepStatus('save', 'done', `Đã ghi ${r.saved} (${r.count} package)${anchorInfo}`);

    // Bước 2-5: Push từng bước
    const commitsAdded = state.changes.added.length;
    const commitsEdited = state.changes.edited.length;
    const commitsDeleted = state.changes.deleted.length;
    const totalChanges = commitsAdded + commitsEdited + commitsDeleted;
    let commitMsg;
    if (totalChanges === 0) {
      commitMsg = `Update ${state.currentRepo}`;
    } else {
      const parts = [];
      if (commitsAdded)   parts.push(`Add ${commitsAdded} pkg`);
      if (commitsEdited)  parts.push(`Update ${commitsEdited} pkg`);
      if (commitsDeleted) parts.push(`Remove ${commitsDeleted} pkg`);
      commitMsg = parts.join('; ');
    }

    setStepStatus('pull', 'running');
    setStepStatus('add', 'pending');
    setStepStatus('status', 'pending');
    setStepStatus('commit', 'pending');
    setStepStatus('push', 'pending');

    const push = await api(`/api/repo/${state.currentRepo}/push`, {
      method: 'POST',
      body: JSON.stringify({ commit_msg: commitMsg }),
    });

    // Cập nhật các bước dựa trên response
    if (push.pull !== undefined) setStepStatus('pull', 'done', push.pull);
    else setStepStatus('pull', 'done');

    if (push.status !== undefined) {
      setStepStatus('add', 'done');
      if (!push.status) {
        setStepStatus('status', 'done', 'Không có thay đổi');
      } else {
        setStepStatus('status', 'done', push.status.split('\n').slice(0, 8).join('\n'));
      }
    }
    if (push.step === 'nothing-to-commit') {
      setStepStatus('commit', 'skipped', 'Không có thay đổi');
      setStepStatus('push', 'skipped', 'Không có thay đổi');
      toast('✓ Không có thay đổi nào để push.', 'success');
    } else if (push.step === 'done') {
      setStepStatus('commit', 'done', push.commit);
      setStepStatus('push', 'done', push.push);
      toast(`🚀 Push thành công! Commit: "${commitMsg}"`, 'success');
      state.changes = { added: [], edited: [], deleted: [] };
    } else {
      // Lỗi
      const failedStep = push.step;
      const order = ['pull', 'add', 'status', 'commit', 'push'];
      const failedIdx = order.indexOf(failedStep);
      for (let i = 0; i < failedIdx; i++) setStepStatus(order[i], 'done');
      setStepStatus(failedStep, 'error', push.detail || push.message);
      toast(`❌ Lỗi ở bước ${failedStep}: ${push.message}`, 'error');
    }
  } catch (err) {
    toast(`❌ Lỗi: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '';
    delete btn.dataset.loading;
  }
}

// ---------------------------------------------------------------------
// Bind events
// ---------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Tách từng ký tự trong #logo-text thành span.lt.
  // 3 CHỮ CÁI ĐƠN LẺ ngẫu nhiên được đánh dấu "broken" (chớp nhá + nghiêng).
  // Các chữ còn lại đứng im hoàn toàn, không animation.
  const logoText = document.getElementById('logo-text');
  if (logoText && !logoText.dataset.split) {
    logoText.dataset.split = '1';
    const original = logoText.textContent.trim();
    const words = original.split(/\s+/);

    // Thu thập tất cả chữ cái (không tính khoảng trắng) — index trong từ + index tổng
    const allLetters = [];
    words.forEach((word, wi) => {
      [...word].forEach((ch, ci) => {
        allLetters.push({ ch, wi, ci });
      });
    });

    // Chọn ngẫu nhiên đúng 3 chữ cái để broken
    const brokenSet = new Set();
    while (brokenSet.size < Math.min(3, allLetters.length)) {
      brokenSet.add(Math.floor(Math.random() * allLetters.length));
    }

    // 3 hướng nghiêng: phải / trái / ngửa sau
    const directionClasses = ['broken-right', 'broken-left', 'broken-back'];

    let html = '';
    let letterIdx = 0;
    words.forEach((word, wi) => {
      html += `<span class="word">`;
      [...word].forEach(ch => {
        if (brokenSet.has(letterIdx)) {
          // Random 1 trong 3 hướng cho mỗi chữ broken
          const dir = directionClasses[Math.floor(Math.random() * 3)];
          const delay = `-${(Math.random() * 3).toFixed(2)}s`;
          html += `<span class="lt broken ${dir}" style="--bd: ${delay};">${ch}</span>`;
        } else {
          html += `<span class="lt">${ch}</span>`;
        }
        letterIdx++;
      });
      html += '</span>';
      if (wi < words.length - 1) html += '<span class="word space">&nbsp;</span>';
    });
    logoText.innerHTML = html;
  }

  $('#repoSelect').addEventListener('change', e => {
    state.currentRepo = e.target.value;
    if (state.currentRepo) loadRepo();
  });
  $('#btnReload').addEventListener('click', async () => {
    if (!state.currentRepo) {
      toast('Chưa chọn repo nào.', 'error');
      return;
    }
    const btn = $('#btnReload');
    btn.disabled = true;
    await loadRepo();
    btn.disabled = false;
  });
  $('#btnAdd').addEventListener('click', () => openModal(null));
  $('#btnSave').addEventListener('click', saveAll);

  // Phím tắt: ESC đóng modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !$('#modal').classList.contains('hidden')) {
      closeModal();
    }
  });

  // Click vào overlay (nền mờ bên ngoài modal-content) để đóng modal
  $('#modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });

  loadRepositories();

  // Package search + pagination
  let _pkgSearchTimer = null;
  $('#pkgSearchInput')?.addEventListener('input', function () {
    clearTimeout(_pkgSearchTimer);
    _pkgSearchTimer = setTimeout(() => {
      state.pkgSearchQuery = this.value;
      state.pkgPage = 1;
      renderPackageList();
    }, 200);
  });
  $('#pkgPagePrev')?.addEventListener('click', () => {
    if (state.pkgPage > 1) { state.pkgPage--; renderPackageList(); }
  });
  $('#pkgPageNext')?.addEventListener('click', () => {
    state.pkgPage++;
    renderPackageList();
  });

  // Blog pagination
  renderBlogList();
  $('#blogPagePrev')?.addEventListener('click', () => {
    if (state.blogPage > 1) { state.blogPage--; renderBlogList(); }
  });
  $('#blogPageNext')?.addEventListener('click', () => {
    state.blogPage++;
    renderBlogList();
  });
});
