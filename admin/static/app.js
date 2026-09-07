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

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
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
    state.packageFiles = files.packages || [];

    renderMeta();
    renderPackageList();
    // Reset tracking changes cho session mới
    state.changes = { added: [], edited: [], deleted: [] };
    toast(`Đã tải ${state.packages.length} package từ repo "${repo}".`, 'success');
  } catch (err) {
    toast(`Lỗi tải repo: ${err.message}`, 'error');
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
// Render: package list
// ---------------------------------------------------------------------

function renderPackageList() {
  const list = $('#packageList');
  list.innerHTML = '';
  $('#packageCount').textContent = `${state.packages.length} package`;
  $('#emptyHint').classList.toggle('hidden', state.packages.length > 0);

  state.packages.forEach((pkg, idx) => {
    const row = document.createElement('div');
    row.className = 'px-5 py-3 hover:bg-slate-50 flex items-center gap-3';
    row.innerHTML = `
      <div class="flex-shrink-0 w-10 h-10 rounded-md bg-slate-200 overflow-hidden flex items-center justify-center">
        ${pkg.icon
          ? `<img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(pkg.icon)}" class="w-full h-full object-cover" onerror="this.style.display='none'" />`
          : '<span class="text-slate-400 text-xs">no img</span>'}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="font-medium truncate">${escapeHtml(pkg.name || '(chưa có tên)')}</span>
          ${pkg.featured ? '<span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-0.5 rounded-full">featured</span>' : ''}
          ${pkg.isPrivate ? '<span class="bg-slate-200 text-slate-700 text-xs px-2 py-0.5 rounded-full">private</span>' : ''}
          ${pkg.kind ? `<span class="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">${escapeHtml(pkg.kind)}</span>` : ''}
        </div>
        <div class="text-xs text-slate-500 truncate">
          <code>${escapeHtml(pkg.identifier)}</code> · v${escapeHtml(pkg.version || '?')} · ${escapeHtml(pkg.category || '—')}
        </div>
      </div>
      <div class="text-xs text-slate-500 text-right">
        <div>${formatSize(pkg.size)}</div>
        <div class="truncate max-w-[120px]" title="${escapeHtml(pkg.sha256 || '')}">${escapeHtml((pkg.sha256 || '').slice(0, 10))}…</div>
      </div>
      <div class="flex gap-1">
        <button data-action="edit" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100">Sửa</button>
        <button data-action="duplicate" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100" title="Sao chép package này để tạo bản mới">Sao chép</button>
        <button data-action="delete" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50">Xoá</button>
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
    banner: 'assets/banner.png',
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
    const opts = ['<option value="">— chọn file .3105 —</option>'];
    state.packageFiles.forEach(p => {
      const sel = p === current ? 'selected' : '';
      opts.push(`<option value="${escapeHtml(p)}" ${sel}>${escapeHtml(p)}</option>`);
    });
    if (current && !state.packageFiles.includes(current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)} (không tìm thấy)</option>`);
    }
    return opts.join('');
  };

  const defaultScreens = window.DEFAULT_SCREENSHOTS || [];

  return `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">File .3105 (chọn để tự động điền SHA-256 + size)</span>
        <div class="flex gap-2 mt-1">
          <select id="f_download" class="flex-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${packageOptions(pkg.download)}</select>
          <button id="btnAutoFill" type="button" class="px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 text-white text-sm whitespace-nowrap">⚡ Lấy hash và size</button>
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
      <label class="block">
        <span class="text-xs text-slate-500">PublishedAt (ISO 8601, tuỳ chọn)</span>
        <input id="f_publishedAt" value="${escapeHtml(pkg.publishedAt || '')}" placeholder="2026-09-06T10:00:00Z" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <div class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <span>Icon (ảnh đại diện package)</span>
          <span class="text-slate-400" id="iconPickerCurrent"></span>
        </span>
        <div class="flex flex-wrap items-center gap-2 mb-2 mt-1">
          <span class="text-xs text-slate-500">Thư mục ảnh:</span>
          <select id="f_icon_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnIconRefreshFolders" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">↻</button>
          <button type="button" id="btnIconNewFolder" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">+ Thư mục</button>
          <button type="button" id="btnIconUpload" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">⬆ Upload ảnh</button>
          <input type="file" id="f_icon_upload" accept="image/*" multiple class="hidden" />
          <button type="button" id="btnIconToggle" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100 ml-auto">Hiện ảnh</button>
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
          <select id="f_banner_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnBannerRefreshFolders" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">↻</button>
          <button type="button" id="btnBannerNewFolder" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">+ Thư mục</button>
          <button type="button" id="btnBannerUpload" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">⬆ Upload ảnh</button>
          <input type="file" id="f_banner_upload" accept="image/*" multiple class="hidden" />
          <button type="button" id="btnBannerToggle" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100 ml-auto">Hiện ảnh</button>
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
          <select id="f_screen_folder" class="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white">
            <option value="">— root (assets/) —</option>
          </select>
          <button type="button" id="btnRefreshFolders" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">↻</button>
          <button type="button" id="btnNewFolder" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">+ Thư mục</button>
          <button type="button" id="btnUploadImages" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">⬆ Upload ảnh</button>
          <input type="file" id="f_image_upload" accept="image/*" multiple class="hidden" />
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
    files.forEach(path => {
      const item = document.createElement('div');
      const isSelected = path === selected;
      item.className = `relative border rounded-md overflow-hidden cursor-pointer aspect-square ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-slate-200 hover:border-blue-300'}`;
      item.title = path;
      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             class="w-full h-full object-cover" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-blue-500/20 flex items-center justify-center"><span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(path.split('/').pop())}</div>
      `;
      item.addEventListener('click', () => selectIcon(path));
      grid.appendChild(item);
    });
  } catch (err) {
    grid.innerHTML = `<p class="text-xs text-red-400 col-span-8">Lỗi: ${escapeHtml(err.message)}</p>`;
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
    files.forEach(path => {
      const item = document.createElement('div');
      const isSelected = path === selected;
      item.className = `relative border rounded-md overflow-hidden cursor-pointer aspect-square ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-slate-200 hover:border-blue-300'}`;
      item.title = path;
      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             class="w-full h-full object-cover" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-blue-500/20 flex items-center justify-center"><span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(path.split('/').pop())}</div>
      `;
      item.addEventListener('click', () => selectBanner(path));
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
}

function selectBanner(path) {
  const hidden = $('#f_banner');
  if (hidden) hidden.value = path;
  updatePickerCurrentLabels();
  refreshBannerPicker();
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
    files.forEach(path => {
      const isSelected = currentSelectedScreens.includes(path);
      const item = document.createElement('div');
      item.className = 'relative group aspect-video rounded-lg overflow-hidden border-2 cursor-pointer select-none ' +
        (isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200 hover:border-slate-400');
      item.dataset.path = path;
      item.draggable = true;
      item.title = path;

      item.innerHTML = `
        <img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"
             class="w-full h-full object-cover" onerror="this.style.display='none'" />
        ${isSelected ? '<div class="absolute inset-0 bg-blue-500/20 flex items-center justify-center"><span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span></div>' : ''}
        <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">${escapeHtml(path.split('/').pop())}</div>
      `;

      item.addEventListener('click', () => {
        const idx = currentSelectedScreens.indexOf(path);
        if (idx >= 0) {
          currentSelectedScreens.splice(idx, 1);
        } else {
          currentSelectedScreens.push(path);
        }
        item.classList.toggle('border-blue-500', currentSelectedScreens.includes(path));
        item.classList.toggle('ring-2', currentSelectedScreens.includes(path));
        item.classList.toggle('ring-blue-200', currentSelectedScreens.includes(path));
        item.classList.toggle('border-slate-200', !currentSelectedScreens.includes(path));
        const overlay = item.querySelector('.bg-blue-500\\/20');
        if (currentSelectedScreens.includes(path)) {
          if (!overlay) {
            const div = document.createElement('div');
            div.className = 'absolute inset-0 bg-blue-500/20 flex items-center justify-center';
            div.innerHTML = '<span class="bg-blue-500 text-white text-xs px-1 rounded">✓</span>';
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
  $('#btnAutoFill')?.addEventListener('click', async () => {
    const path = $('#f_download').value;
    if (!path) { toast('Chọn file .3105 trước đã.', 'error'); return; }
    try {
      const r = await api(`/api/repo/${state.currentRepo}/hash`, {
        method: 'POST',
        body: JSON.stringify({ path }),
      });
      $('#f_download').value = r.path;
      $('#f_sha256').value = r.sha256;
      $('#f_size').value = r.size;
      toast(`Đã lấy hash + size cho ${r.path}`, 'success');
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });

  $('#f_use_default_screens')?.addEventListener('change', e => {
    $('#screensListWrap').style.display = e.target.checked ? 'none' : 'block';
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
      state.packageFiles = list.packages || [];
      // Cập nhật lại <select id="f_download"> mà không re-render toàn bộ form
      const sel = $('#f_download');
      if (sel) {
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">— chọn file .3105 —</option>' +
          state.packageFiles.map(p =>
            `<option value="${escapeHtml(p)}" ${p === currentVal ? 'selected' : ''}>${escapeHtml(p)}</option>`
          ).join('');
        if (currentVal) sel.value = currentVal;
      }
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  }

  $('#f_screen_folder')?.addEventListener('change', e => {
    currentScreenFolder = e.target.value;
    refreshScreenGrid();
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
    publishedAt: $('#f_publishedAt').value.trim(),
    icon: $('#f_icon').value,
    banner: $('#f_banner').value,
    __use_default_screens: $('#f_use_default_screens').checked,
    screenshots: currentSelectedScreens.slice(),
    download: $('#f_download').value,
    sha256: normalizeSha256($('#f_sha256').value),
    size: parseInt($('#f_size').value, 10) || 0,
    password: $('#f_password').value,
    featured: $('#f_featured').checked,
    isPrivate: $('#f_isPrivate').checked,
    __use_default_os: $('#f_use_default_os').checked,
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

  if (state.editingIndex === null) {
    state.packages.push(pkgClean);
    state.packagesMeta.push({
      use_anchor_os: useOs,
      use_anchor_screens: useScreens,
    });
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
  if (state.packages.length === 0 && state.changes.deleted.length === 0) {
    if (!confirm('Repo không có package nào. Vẫn ghi file?')) return;
  }

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

  const commitMsg = buildCommitMessage();

  // Disable nút để tránh double-click
  const btn = $('#btnSave');
  btn.disabled = true;
  btn.textContent = '⏳ Đang lưu...';

  try {
    // Bước 1: Ghi file YAML
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
    toast(`✓ Đã ghi file ${r.saved} (${r.count} package)${anchorInfo}. Đang push...`, 'info');

    // Bước 2: Push lên GitHub
    const push = await api(`/api/repo/${state.currentRepo}/push`, {
      method: 'POST',
      body: JSON.stringify({ commit_msg: commitMsg }),
    });

    if (push.step === 'nothing-to-commit') {
      toast('✓ Không có thay đổi nào. Git đã sạch.', 'success');
    } else {
      toast(`🚀 Push thành công! Commit: "${commitMsg}"`, 'success');
    }
    // Reset changes sau khi push thành công
    state.changes = { added: [], edited: [], deleted: [] };
  } catch (err) {
    toast(`Lỗi: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🚀 Lưu & Push Git';
  }
}

// ---------------------------------------------------------------------
// Bind events
// ---------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  $('#repoSelect').addEventListener('change', e => {
    state.currentRepo = e.target.value;
    if (state.currentRepo) loadRepo();
  });
  $('#btnReload').addEventListener('click', loadRepo);
  $('#btnAdd').addEventListener('click', () => openModal(null));
  $('#btnSave').addEventListener('click', saveAll);

  // Phím tắt: ESC đóng modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !$('#modal').classList.contains('hidden')) {
      closeModal();
    }
  });

  loadRepositories();
});
